
import sys
from pathlib import Path
# Add parent directory to sys.path
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from core.server_manager import ServerManager
from tools.search_tool import search_web_tavily
from tools.weather import get_weather

# 1. Initialize Manager
manager = ServerManager()

# 2. Create Server Instance
# Industry tip: Use specific instructions so the LLM knows the server's purpose
mcp = manager.server_implementation(
    instructions="A collection of tools for web searching and weather retrieval."
)

# 3. Explicit Tool Registration
# Registering via function allows us to control which tools are exposed
mcp.tool(name="search_web")(search_web_tavily)
mcp.tool(name="get_weather")(get_weather)

if __name__ == "__main__":
    # In production, this would be called by an MCP Host (like Claude Desktop or your own Client)
    mcp.run()