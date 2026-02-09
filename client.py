from client.client_manager import ClientManager
import asyncio

async def main():
    manager = ClientManager()
    print(manager.is_initialised)
    agent = manager.client_initialization()
    print(manager.is_initialised)
    tools = await manager.get_client_tools()
    print(tools)
    
asyncio.run(main())
