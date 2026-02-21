from typing import TypedDict, Annotated, List, Dict, Optional, Any
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langgraph.types import Command
from langgraph.graph.state import CompiledStateGraph
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage,ToolMessage
from langchain_core.runnables import Runnable
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from config.settings import settings 
from core.database_manager import Database_Manager
from client.client_manager import ClientManager

class ChatBotState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

class Agent_Manager:
    def __init__(self, 
                 model_name: str = None, 
                 model_temperature: float = None,
                 database_manager: Database_Manager = None,
                 client_manager: ClientManager = None):
        
        self.model_name = model_name or settings.LLM_MODEL
        self.model_temperature = model_temperature or settings.LLM_TEMPERATURE
        
        self.database_manager = database_manager or Database_Manager()
        self.client_manager = client_manager or ClientManager()
        
        self.llm = ChatGroq(
            model=self.model_name,
            temperature=self.model_temperature,
            api_key=settings.GROQ_API_KEY
        )
        
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are a professional AI assistant with access to GitHub via MCP tools. "
                "Always confirm with the user before performing destructive actions like deleting repositories. "
                "If a user denies an action, acknowledge it gracefully and ask for the next step."
            )),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        self.checkpointer: Optional[AsyncSqliteSaver] = None
        self.llm_with_tools: Optional[Runnable] = None
        self._agent: Optional[CompiledStateGraph] = None

    @property
    def is_initialised_agent(self) -> bool:
        return self._agent is not None
    
    async def _call_model(self, state: ChatBotState) -> Dict:
        """Node function to process messages."""
        chain = self.prompt | self.llm_with_tools
        response = await chain.ainvoke(state)
        return {"messages": [response]}

    async def initialize(self) -> CompiledStateGraph:
        """Initialize DB, Fetch MCP Tools, and Compile Graph with Breakpoints."""
        # 1. Setup DB Checkpointer
        self.checkpointer = await self.database_manager.connection()
        
        # 2. Get tools from MCP Client
        tools = await self.client_manager.get_client_tools()
        
        # 3. Bind tools to LLM
        self.llm_with_tools = self.llm.bind_tools(tools)
        
        # 4. Build Graph
        workflow = StateGraph(ChatBotState)
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", ToolNode(tools))

        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", tools_condition)
        workflow.add_edge("tools", "agent")
        
        # 5. Compile with interrupt_before for HITL
        self._agent = workflow.compile(
            checkpointer=self.checkpointer,
            interrupt_before=["tools"]
        )
        
        return self._agent

    @property
    def agent(self) -> CompiledStateGraph:
        if not self._agent:
            raise RuntimeError("Agent not initialized. Call 'await manager.initialize()' first.")
        return self._agent
    
    async def get_response(self, user_input: str, thread_id: str = "default") -> str:
        """
        Processes a single user message and returns the final text answer.
        """
        config = {"configurable": {"thread_id": thread_id}}
        
        input_data = {"messages": [HumanMessage(content=user_input)]}

        final_state = await self.agent.ainvoke(input_data, config=config)
        return final_state["messages"][-1].content
    
    async def get_streaming_response(self, user_input: str, thread_id: str):
        """Streams response and handles the state transition."""
        config = {"configurable": {"thread_id": thread_id}}
        input_data = {"messages": [HumanMessage(content=user_input)]}

        # We use astream to yield updates
        async for message, metadata in self.agent.astream(
            input_data, 
            config=config, 
            stream_mode="messages"
        ):
            if isinstance(message, AIMessage) and message.content:
                yield message.content

    async def get_streaming_response1(self, user_input: str, config: Dict):
        """Streams response and handles the state transition."""

        async for event in self.agent.astream({"messages": [("user", user_input)]}, config, stream_mode="updates"):
            for node_name, output in event.items():
                if node_name == "agent":
                    msg = output["messages"][-1]
                    if msg.content:
                        print(f"AI: {msg.content}")

        # 2. HITL (Human-In-The-Loop) Logic
        state = await self.agent.aget_state(config)
        
        # This 'while' loop catches tool calls even if there are multiple in a row
        while state.next and "tools" in state.next:
            last_ai_msg = state.values["messages"][-1]
            
            for tool_call in last_ai_msg.tool_calls:
                t_name = tool_call["name"]
                t_args = tool_call["args"]
                t_id = tool_call["id"]

                # --- GUARDRAIL: Limit repository lists to keep terminal clean ---
                if t_name == "list_repositories" and t_args.get("limit", 0) > 10:
                    t_args["limit"] = 10

                # --- SECURITY CHECK: Dangerous Actions ---
                if t_name in ["delete_repository", "create_repository"]:
                    print(f"\n🛑 [SECURITY CHECK]: AI wants to {t_name}")
                    print(f"Details: {t_args}")
                    confirm = input("Allow this? (y/n): ").lower()

                    if confirm != 'y':
                        # STEP 1: Create the "Injection" message to tell the AI it was denied
                        reject_msg = ToolMessage(
                            tool_call_id=t_id,
                            name=t_name,
                            content=f"USER DENIED: The human user has explicitly rejected the {t_name} action for security reasons. Acknowledge this and stop."
                        )
                        
                        # STEP 2: Update the state ACTING AS the 'tools' node
                        # This skips the real GitHub call and records the rejection
                        await self.agent.aupdate_state(config, {"messages": [reject_msg]}, as_node="tools")
                        
                        print("System: Action blocked. Informing AI...")
                        
                        # STEP 3: Let the AI respond to the rejection
                        async for update in self.agent.astream(None, config, stream_mode="updates"):
                            if "agent" in update:
                                final_msg = update["agent"]["messages"][-1]
                                if final_msg.content:
                                    print(f"AI: {final_msg.content}")
                        break # Break out of the tool loop for this rejection
                
                # --- EXECUTION: If approved or safe tool ---
                print(f"🚀 Running {t_name}...")
                async for update in self.agent.astream(Command(resume=True), config, stream_mode="updates"):
                    if "agent" in update:
                        final_msg = update["agent"]["messages"][-1]
                        if final_msg.content:
                            print(f"AI: {final_msg.content}")

            # Refresh state to see if the AI wants to do anything else
            state = await self.agent.aget_state(config)