
import sys
from pathlib import Path

# Add parent directory to sys.path for modular imports
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from core.server_manager import ServerManager
from tools.search_tool import search_web_tavily
from tools.weather import get_weather

# 1. Initialize Manager
manager = ServerManager()

# 2. Create Server Instance
# The 'instructions' help the LLM understand when to use this specific server
mcp = manager.server_implementation(
    instructions="Use these tools to fetch real-time weather and perform web searches."
)

# 3. Tool Registration
# FastMCP automatically handles 'async def' functions correctly
mcp.tool(name="search_web_tavily")(search_web_tavily)
mcp.tool(name="get_weather")(get_weather)

if __name__ == "__main__":
    # run() starts the stdio transport by default, which is perfect for your ClientManager
    mcp.run()