import sqlite3

try:
    conn = sqlite3.connect("I:/claude2/kaku_hegemony_v2.db", timeout=2)
    cur = conn.cursor()
    cur.execute("PRAGMA journal_mode=WAL;")
    cur.execute("BEGIN IMMEDIATE;")
    print("Lock acquired successfully!")
    conn.commit()
    conn.close()
except Exception as e:
    print(f"Error acquiring lock: {e}")

