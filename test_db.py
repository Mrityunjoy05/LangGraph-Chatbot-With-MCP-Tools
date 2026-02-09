
from core.database_manager import Database_Manager
import asyncio

async def main():
    db = Database_Manager()

    print(db.is_initialised_conn)
    print(db.is_initialised)

    checkpointer = await db.connection()
    print(db.is_initialised_conn)
    print(db.is_initialised)
    print(checkpointer)
    print(type(checkpointer))
    print(db.database_path)
    await db.close_connection()
asyncio.run(main())