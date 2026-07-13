import os
import sqlite3

db_path = "kaku_hegemony_v2.db"
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("PRAGMA table_info(plot);")
    for row in cursor.fetchall():
        print(row)
    conn.close()
else:
    print("DB file not found")

