import sqlite3


def check_db():
    conn = sqlite3.connect('kaku_hegemony_v2.db')
    cursor = conn.cursor()

    print("--- Tables ---")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [r[0] for r in cursor.fetchall()]
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"{table}: {count} rows")

    print("\n--- Recent Books ---")
    cursor.execute("SELECT id, title, created_at FROM books ORDER BY created_at DESC LIMIT 5")
    for row in cursor.fetchall():
        print(row)

if __name__ == "__main__":
    check_db()

