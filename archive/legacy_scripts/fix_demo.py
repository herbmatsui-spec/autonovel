
f = r"I:\claude2\demo.py"
with open(f, "r", encoding="utf-8") as file:
    content = file.read()

content = content.replace("from src.core.db import DBManager", "from src.backend.database.core import DatabaseManager, init_db\nimport config\nimport config.base")

old_init = """    db_manager = DBManager("sqlite+aiosqlite:///demo_hegemony.db")
    await db_manager.init_db()"""

new_init = """    db_url = "sqlite+aiosqlite:///demo_hegemony.db"
    config.DATABASE_URL = db_url
    config.base.DATABASE_URL = db_url
    init_db("demo_hegemony.db")
    db_manager = DatabaseManager(db_url)"""

content = content.replace(old_init, new_init)

with open(f, "w", encoding="utf-8") as file:
    file.write(content)
print("demo.py updated successfully.")

