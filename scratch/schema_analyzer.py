import sqlite3
import sys

DB_PATH = 'i:/claude2/kaku_hegemony_v2.db'
TABLES = [
    'books', 'custom_styles', 'internal_state', 'style_fragments', 'bible',
    'branches', 'chapters', 'characters', 'optimization_history', 'pending_patches',
    'rules', 'masterpieces', 'outbox', 'background_tasks', 'audit_issues',
    'foreshadowing', 'character_arcs', 'plot', 'prompt_versions'
]

def analyze_schema():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        print(f"Analyzing schema for: {DB_PATH}\n")

        for table in TABLES:
            print(f"--- Table: {table} ---")
            cursor.execute(f"PRAGMA table_info({table})")
            columns = cursor.fetchall()
            if not columns:
                print("  No columns found or table does not exist.")
                continue

            for col in columns:
                # col: (cid, name, type, notnull, dflt_value, pk)
                print(f"  Column: {col[1]} | Type: {col[2]} | NotNull: {col[3]} | PK: {col[5]}")

            # Check for indexes
            cursor.execute(f"PRAGMA index_list({table})")
            indexes = cursor.fetchall()
            for idx in indexes:
                # idx: (seq, name, unique, origin)
                print(f"  Index: {idx[1]} | Unique: {idx[2]}")
            print("\n")

        conn.close()
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    analyze_schema()

