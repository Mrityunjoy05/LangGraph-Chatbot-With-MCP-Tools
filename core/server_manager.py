from fastmcp import FastMCP 
from config.settings import settings
from typing import Optional

class ServerManager:
    def __init__(self, server_name: Optional[str] = None):
        self.server_name: str = server_name or settings.WEB_SERVER_NAME
        self._server: Optional[FastMCP] = None

    @property
    def server(self) -> FastMCP:
        if not self._server:
            raise RuntimeError("Server not initialized. Call server_implementation first.")
        return self._server
    
    @property
    def is_initialised(self) -> bool:
        return self._server is not None

    def server_implementation(self, instructions: str = "") -> FastMCP:
        """Initializes the FastMCP server instance."""
        self._server = FastMCP(
            name=self.server_name, 
            instructions=instructions
        )
        return self._server
    