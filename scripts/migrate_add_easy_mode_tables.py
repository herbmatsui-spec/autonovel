"""
 Standalone DB migration script for Step 6 & 7 of Easy Mode Suite implementation plan.
 Run with: python scripts/migrate_add_easy_mode_tables.py

 Adds:
   - books.mode TEXT DEFAULT 'easy' NOT NULL
   - easy_mode_drafts table (new)
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "autonovel.db"


def get_conn():
    return sqlite3.connect(DB_PATH)


def migrate():
    if not DB_PATH.exists():
        print(f"[migrate] DB not found at {DB_PATH}, skipping migration.")
        return

    conn = get_conn()
    cur = conn.cursor()

    print(f"[migrate] Connected to {DB_PATH}")

    # --- Step 6: Add books.mode column ---
    cur.execute("PRAGMA table_info(books)")
    columns = {row[1] for row in cur.fetchall()}

    if "mode" not in columns:
        print("[migrate] Adding books.mode column...")
        cur.execute("ALTER TABLE books ADD COLUMN mode TEXT DEFAULT 'easy' NOT NULL")
        print("[migrate] books.mode column added.")
    else:
        print("[migrate] books.mode already exists, skipping.")

    # --- Step 7: Create easy_mode_drafts table ---
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='easy_mode_drafts'"
    )
    if cur.fetchone() is None:
        print("[migrate] Creating easy_mode_drafts table...")
        cur.execute("""
            CREATE TABLE easy_mode_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                draft_id TEXT UNIQUE NOT NULL,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL DEFAULT '{}',
                parent_draft_id TEXT,
                book_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute(
            "CREATE INDEX idx_easy_mode_drafts_kind ON easy_mode_drafts(kind)"
        )
        cur.execute(
            "CREATE INDEX idx_easy_mode_drafts_created ON easy_mode_drafts(created_at)"
        )
        print("[migrate] easy_mode_drafts table created.")
    else:
        print("[migrate] easy_mode_drafts already exists, skipping.")

    conn.commit()
    conn.close()
    print("[migrate] Migration complete.")


if __name__ == "__main__":
    migrate()
