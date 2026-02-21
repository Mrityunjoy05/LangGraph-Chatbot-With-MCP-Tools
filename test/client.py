import sys
from pathlib import Path
file_dir = Path(__file__).parent.parent
if str(file_dir) not in sys.path:
    sys.path.insert(0, str(file_dir))

from client.client_manager import ClientManager
import asyncio




async def main():
    
    manager = ClientManager()
    print(manager.is_initialised)
    agent = manager.client_initialization()
    print(manager.is_initialised)
    tools = await manager.get_client_tools()
    print(tools)
    print(manager.base_dir)
    print(manager.server_dir)
    
    print("\n File Dir :- \n")
    file_dir = Path(__file__).parent.parent
    print(file_dir)

asyncio.run(main())
