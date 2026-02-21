
from langchain_mcp_adapters.client import MultiServerMCPClient
from pathlib import Path
from typing import Dict, List, Any , Optional
from config.settings import settings
class ClientManager:
    def __init__(self):
        self.base_dir: Path = Path(__file__).parent.parent
        self.server_dir : str = self.base_dir /settings.SERVER_FOLDER_NAME
        self._client: Optional[MultiServerMCPClient] = None
        self._serverState: Dict = None

    @property
    def is_initialised(self) -> bool:
        return self._client is not None

    @property
    def client(self) -> MultiServerMCPClient:
        return self._client
    
    def client_initialization(self) -> MultiServerMCPClient:
        # Using the exact dictionary structure you provided
        self._serverState = {
            settings.WEB_SERVER_NAME: {
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
                    "chatbot_server.py"
                ]
            },
            settings.GITHUB_SERVER_NAME: {
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
                    "github_mcp_server.py"
                ]
            }
        }
        self._client = MultiServerMCPClient(self._serverState)
        return self._client
    
    async def get_client_tools(self) -> List[Any]:
        if not self.is_initialised:
            self.client_initialization()

        tools = await self._client.get_tools()
        return tools
    