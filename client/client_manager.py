from langchain_mcp_adapters.client import MultiServerMCPClient
from pathlib import Path
from fastmcp import FastMCP
from typing import Dict

class ClientManager:

    def __init__(self ):
        self.base_dir : Path = Path(__file__).parent.parent
        self.server_dir : str = self.base_dir

        self._client : FastMCP = None
        self._serverState : Dict = None
    
    @property
    def is_initialised(self) -> bool:
        return self._client is not None

    @property
    def client(self):

        return self._client
    
    def client_initialization(self):
        self._serverState  = {
            "math": {
                "transport": "stdio",
                "command": "uv",
                "env": {
                    "PYTHONPATH": str(self.base_dir)  
                },
                "args": [
                    "--directory",
                    str(self.server_dir),
                    "run",
                    "fastmcp",
                    "run",
                    "local_server.py"
                ]
            }
        }
        self._client = MultiServerMCPClient(self._serverState)

        return self._client
    
    def get_client_tools(self):

        if not self.is_initialised:
            raise ValueError("Initialise the client first Using 'client_initialization'.")
        
        tools = self._client.get_tools()
        return tools