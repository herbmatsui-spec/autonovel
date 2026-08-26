import sqlite3

conn = sqlite3.connect('E:\\aaaaaa\\autonovel.db')

queries = [
    "ALTER TABLE books ADD COLUMN cumulative_tension FLOAT DEFAULT 0.0;",
    "ALTER TABLE books ADD COLUMN cumulative_qol FLOAT DEFAULT 0.0;",
    "ALTER TABLE books ADD COLUMN cumulative_cost FLOAT DEFAULT 0.0;",
    "ALTER TABLE books ADD COLUMN sanctuary_integrity FLOAT DEFAULT 100.0;",
    "ALTER TABLE books ADD COLUMN current_branch_id VARCHAR(50) DEFAULT NULL;",
]

for q in queries:
    try:
        conn.execute(q)
        print(f"Executed: {q}")
    except Exception as e:
        print(f"Error executing {q}: {e}")

conn.commit()
print("Done")
