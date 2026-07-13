import logging
import os
import sqlite3

from backend.database import DatabaseManager

logging.basicConfig(level=logging.INFO)

db_path = "test_corruption.db"

def setup_corrupt_db():
    if os.path.exists(db_path):
        os.remove(db_path)

    # Create a valid DB first
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY);")
    conn.execute("INSERT INTO test VALUES (1);")
    conn.commit()
    conn.close()

    # Corrupt it by overwriting the header or random parts
    with open(db_path, "r+b") as f:
        f.seek(100) # Past the header
        f.write(b"this is corruption" * 100)

def test_recovery():
    print("--- Starting recovery test ---")
    setup_corrupt_db()

    manager = DatabaseManager(db_path)

    print("Attempting to start manager with corrupted DB...")
    manager.start()

    print("Checking if recovery happened...")
    if os.path.exists(db_path):
        conn = sqlite3.connect(db_path)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"Tables in new DB: {tables}")
        conn.close()

        if "books" in tables and "plot" in tables:
            print("SUCCESS: Database recovered and schema created.")
        else:
            print("FAILURE: Database file exists but schema is missing.")
    else:
        print("FAILURE: Database file not found after recovery attempt.")

    # Check for .corrupt_ file
    corrupt_files = [f for f in os.listdir(".") if f.startswith(db_path + ".corrupt_")]
    if corrupt_files:
        print(f"SUCCESS: Found corrupted backup file: {corrupt_files[0]}")
        for f in corrupt_files: os.remove(f)
    else:
        print("FAILURE: Corrupted backup file not found.")

    if os.path.exists(db_path):
        os.remove(db_path)

if __name__ == "__main__":
    test_recovery()

