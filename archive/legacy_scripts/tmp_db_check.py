import sys
sys.path.insert(0, r"I:\R15\cR15")
from src.backend.database import Container
dbm = Container.db()
print("DB URL:", dbm.engine.url)
print("Database connected successfully")