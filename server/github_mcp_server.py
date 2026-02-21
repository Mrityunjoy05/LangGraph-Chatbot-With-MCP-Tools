
import sys
from pathlib import Path

# Add parent directory to sys.path for modular imports
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from core.server_manager import ServerManager
from config.settings import settings
from tools.delete_repository import delete_repository
from tools.create_repository import create_repository 
from tools.list_repositories import list_repositories 

# 1. Initialize Manager
manager = ServerManager(server_name=settings.GITHUB_SERVER_NAME)


# 2. Create Server Instance
# The 'instructions' help the LLM understand when to use this specific server
mcp = manager.server_implementation(
    instructions="GitHub tools for AI agents - Create, Read, Delete repos & more"
)

# 3. Tool Registration
# FastMCP automatically handles 'async def' functions correctly
mcp.tool(name="delete_repository")(delete_repository)
mcp.tool(name="create_repository")(create_repository)
mcp.tool(name="list_repositories")(list_repositories)
    
if __name__ == '__main__':
    mcp.run(transport='stdio')
