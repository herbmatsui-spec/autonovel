import logging
import sqlite3
import sys

import psycopg2
from psycopg2 import extras

# 設定
SQLITE_DB_PATH = 'i:/claude2/kaku_hegemony_v2.db'
PG_CONN_PARAMS = {
    "dbname": "kaku_hegemony_db",
    "user": "postgres",
    "password": "password",
    "host": "localhost",
    "port": "5432"
}

# 移行対象テーブル (依存関係を考慮した順序)
TABLES = [
    'books', 'custom_styles', 'internal_state', 'style_fragments',
    'bible', 'branches', 'chapters', 'characters', 'optimization_history',
    'pending_patches', 'rules', 'masterpieces', 'outbox', 'background_tasks',
    'audit_issues', 'foreshadowing', 'character_arcs', 'plot', 'prompt_versions'
]

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def migrate_table(sqlite_cursor, pg_cursor, table_name):
    logger.info(f"Migrating table: {table_name}...")

    # 1. SQLiteから全データを取得
    sqlite_cursor.execute(f"SELECT * FROM {table_name}")
    rows = sqlite_cursor.fetchall()

    if not rows:
        logger.info(f"No data found in {table_name}. Skipping.")
        return

    # 2. カラム名を取得
    col_names = [description[0] for description in sqlite_cursor.description]

    # 3. PostgreSQLへのインサートクエリ作成
    # %s プレースホルダーをカラム数分作成
    placeholders = ",".join(["%s"] * len(col_names))
    columns_str = ",".join([f'"{col}"' for col in col_names])
    insert_query = f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'

    try:
        # execute_values を使用してバッチインサート (高速)
        extras.execute_values(pg_cursor, insert_query, rows)
        logger.info(f"Successfully migrated {len(rows)} rows to {table_name}.")
    except Exception as e:
        logger.error(f"Error migrating {table_name}: {e}")
        raise e

def main():
    sqlite_conn = None
    pg_conn = None

    try:
        # 接続
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        sqlite_cursor = sqlite_conn.cursor()

        pg_conn = psycopg2.connect(**PG_CONN_PARAMS)
        pg_cursor = pg_conn.cursor()

        # トランザクション開始
        for table in TABLES:
            migrate_table(sqlite_cursor, pg_cursor, table)

        pg_conn.commit()
        logger.info("Migration completed successfully!")

    except Exception as e:
        if pg_conn:
            pg_conn.rollback()
        logger.error(f"Migration failed: {e}")
        sys.exit(1)
    finally:
        if sqlite_conn: sqlite_conn.close()
        if pg_conn: pg_conn.close()

if __name__ == "__main__":
    main()

