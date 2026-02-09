from typing import TypedDict, Annotated, List, Dict, Optional, Any
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph

from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage , HumanMessage , AIMessage
from langchain_core.runnables import Runnable
from langchain_core.prompts import ChatPromptTemplate , MessagesPlaceholder
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
            ("system", "You are a helpful and professional AI assistant. "
                       "You have access to real-time tools via MCP. "
                       "Always use tools when you need factual or current information."
                       "Use search_web_tavily tool for any web search"
                       ),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        self.llm_with_tools : Optional[Runnable]= None
        self._graph : Optional[StateGraph]= None
        self._agent: Optional[CompiledStateGraph] = None

    @property
    def is_initialised_agent(self) -> bool:
        return self._agent is not None
    
    @property
    def is_initialised_graph(self) -> bool:
        return self._graph is not None
    
    async def _call_model(self, state: ChatBotState) -> Dict:
        """
        The Node function that processes messages using Prompt + Bound LLM.
        """
        # Create a chain: Prompt -> LLM (with tools)
        chain = self.prompt | self.llm_with_tools
        
        # Pass the current state to the chain
        response = await chain.ainvoke(state)
        return {"messages": [response]}

    async def initialize(self) -> CompiledStateGraph:
        """
        Async entry point to wire up DB and MCP Tools.
        """
        # 1. Setup DB Checkpointer
        checkpointer = await self.database_manager.connection()
        
        # 2. Get tools from MCP Client
        tools = await self.client_manager.get_client_tools()
        
        # 3. BIND TOOLS to the LLM
        # This creates the version of the LLM that knows how to call your MCP tools
        self.llm_with_tools = self.llm.bind_tools(tools)
        
        # 4. Build Graph
        workflow = StateGraph(ChatBotState)
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", ToolNode(tools))

        workflow.add_edge(START, "agent")
        workflow.add_conditional_edges("agent", tools_condition)
        workflow.add_edge("tools", "agent")
        
        self._graph = workflow

        self._agent = workflow.compile(checkpointer=checkpointer)
        
        print("Agent Manager: Tools bound and Graph compiled (Async).")
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
    
    async def get_streaming_response(self, user_input: str, thread_id: str = "default"):
        """
        Streams message chunks using 'messages' mode. 
        This is the most efficient way to get incremental updates.
        """
        config = {"configurable": {"thread_id": thread_id}}
        # Note: input_data messages should still be in a list []
        input_data = {"messages": [HumanMessage(content=user_input)]}

        try:
            # 'messages' mode yields tuples: (BaseMessage, metadata)
            async for message, metadata in self.agent.astream(
                input_data, 
                config=config, 
                stream_mode="messages"
            ):
                # We check if the message has content (filters out empty metadata chunks)
                if isinstance(message , AIMessage):
                    yield message.content
        except Exception as e:
            yield f"Streaming error: {str(e)}"
    
        