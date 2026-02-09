from langgraph.graph import StateGraph , START , END
from langgraph.prebuilt import ToolNode , tools_condition
from langgraph.graph.message import add_messages
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.state import CompiledStateGraph

from langchain_groq import ChatGroq

from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage , AIMessage ,BaseMessage

from typing import TypedDict , Annotated ,List , Dict
from config.settings import settings 
from core.database_manager import Database_Manager
from client import get_client_tools

# PRO-TIP: Define State globally for modular imports
class ChatBotState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]

class Agent_Manager:
    def __init__(self, model_name: str = None, model_temperature: float = None):
        # 1. Setup Configuration
        self.model_name = model_name or settings.LLM_MODEL
        self.model_temperature = model_temperature or settings.LLM_TEMPERATURE
        
        # 2. Setup Database (Your modular DB manager)
        self.db_manager = Database_Manager()
        self.checkpointer = self.db_manager.connection()

        # 3. Setup LLM
        self.llm = ChatGroq(
            model=self.model_name,
            temperature=self.model_temperature,
            groq_api_key=settings.GROQ_API_KEY
        )
        
        # 4. Compile the Graph immediately
        self._graph = None
        self._agent = None

    @property
    def is_initialised_agent(self) -> bool:
        return self._agent is not None
    
    @property
    def is_initialised_graph(self) -> bool:
        return self._graph is not None
    
    @property
    def agent(self) -> CompiledStateGraph:
        if not self._agent:
            raise RuntimeError("Agent not initialized. Call .initialize() first.")
        return self._agent
    
    def _call_model(self, state: ChatBotState) -> Dict[str, List[BaseMessage]]:
        """Node Logic: Processes the messages through the LLM."""
        response = self.llm.invoke(state["messages"])
        return {"messages": [response]}

    def _build_workflow(self) -> StateGraph:
        """Constructs the blueprint (StateGraph) of the graph."""
        workflow = StateGraph(ChatBotState)

        # Add nodes
        workflow.add_node("chatbot_node", self._call_model)

        # Define edges
        workflow.add_edge(START, "chatbot_node")
        workflow.add_edge("chatbot_node", END)
        
        return workflow
    
    def initialize(self) -> CompiledStateGraph:
        """Finalizes the workflow and compiles it into a runnable agent."""
        # Set the workflow layout (The Blueprint)
        self._graph = self._build_workflow()
        
        # Compile it with the checkpointer (The Runnable)
        self._agent = self._graph.compile(checkpointer=self.checkpointer)
        
        print("Modular Agent system fully initialized.")
        return self._agent


