import sys

sys.path.insert(0, r"I:\R15\cR15")

try:
    from config.container import Container
    from src.backend.database import init_db

    print("Imports successful")

    dbm = Container.db()
    print("Got db manager:", type(dbm))

    print("Calling init_db...")
    init_db(dbm.db_path)
    print("init_db completed")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
