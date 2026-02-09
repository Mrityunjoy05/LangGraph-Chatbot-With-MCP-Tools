import aiosqlite
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from config.settings import settings
from pathlib import Path
from typing import Optional

class Database_Manager:
    def __init__(self, database_name: str = None, db_folder: str = None):
        self.database_name = database_name or settings.DATABASE_NAME
        self.db_folder = db_folder or settings.DB_FOLDER_NAME
        self._database_path: Optional[Path] = None
        self._conn: Optional[aiosqlite.Connection] = None
        self._checkpointer: Optional[AsyncSqliteSaver] = None

    @property
    def is_initialised_conn(self) -> bool:
        return self._conn is not None
    
    @property
    def is_initialised(self) -> bool:
        return self._checkpointer is not None

    @property
    def checkpointer(self) -> AsyncSqliteSaver:
        if not self._checkpointer:
            raise RuntimeError("Database not initialized. Call connection() first.")
        return self._checkpointer

    @property
    def conn(self):

        return  self._conn
    
    @property
    def database_path(self):

        return  self._database_path
    
    async def database_initialization(self):
        database_folder = Path(__file__).resolve().parent.parent / self.db_folder
        database_folder.mkdir(exist_ok=True)
        self._database_path = database_folder / self.database_name
        self._conn = await aiosqlite.connect(database=self._database_path, check_same_thread=False)
        return self._conn

    async def checkpoint_initialization(self):

        self._checkpointer = AsyncSqliteSaver(conn=self._conn)

        return self._checkpointer
    
    async def connection(self) -> AsyncSqliteSaver:
        if not self.is_initialised_conn:
            await self.database_initialization()
        if not self.is_initialised:
            await self.checkpoint_initialization()
            
        return self._checkpointer
    
    async def close_connection(self):
        """Cleanup method for production shutdown."""
        if self._conn:
            await self._conn.close()
            self._conn = None