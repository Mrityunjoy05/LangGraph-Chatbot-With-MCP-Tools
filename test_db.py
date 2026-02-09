
from core.database_manager import Database_Manager

db = Database_Manager()

print(db.is_initialised_conn)
print(db.is_initialised)
checkpointer = db.connection()
print(db.is_initialised_conn)
print(db.is_initialised)
print(checkpointer)
print(type(checkpointer))
print(db.database_path)
