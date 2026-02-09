from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
from config.settings import settings

from pathlib import Path


class Database_Manager:


    def __init__(self , database_name : str = None , db_folder : str = None ):
        
        self.database_name = database_name or settings.DATABASE_NAME
        self.db_folder = db_folder or settings.DB_FOLDER_NAME

        self._database_path : str = None

        self._conn : sqlite3 = None

        self._checkpointer : SqliteSaver = None


    @property
    def is_initialised_conn(self):

        return self._conn is not None
    
    @property
    def is_initialised(self):

        return self._checkpointer is not None
    
    
    
    @property
    def conn(self):

        return  self._conn
    
    @property
    def checkpointer(self):

        return  self._checkpointer
    
    @property
    def database_path(self):

        return  self._database_path
    

    def database_initialization(self ,database_name : str = None , db_folder : str = None ):

        database_name = database_name or self.database_name
        db_folder = db_folder or self.db_folder

        database_folder = Path(__file__).resolve().parent.parent / db_folder
        database_folder.mkdir(exist_ok=True)

        self._database_path = database_folder / database_name

        self._conn = sqlite3.connect(database=self._database_path , check_same_thread=False)

        return self._conn
    

    def checkpoint_initialization(self):

        self._checkpointer = SqliteSaver(conn=self._conn)

        return self._checkpointer

    def connection(self):
        """
        Lazily initializes database connection and LangGraph checkpointer.
        Always returns a ready-to-use SqliteSaver.
        """

        if not self.is_initialised_conn:
            self.database_initialization()

        if not self.is_initialised:
            self.checkpoint_initialization()

        return self._checkpointer

    