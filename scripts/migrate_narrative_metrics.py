import logging

from sqlalchemy import text

from database.core import DatabaseManager


def apply_narrative_metrics_migration():
    """
    narrative_metrics および narrative_metric_definitions テーブルを作成する
    alembicが正しく動作しない環境へのフォールバックとして、直接SQLを実行する。
    """
    db_mgr = DatabaseManager()
    logger = logging.getLogger(__name__)

    # 定義テーブルの作成
    definition_table_sql = """
    CREATE TABLE IF NOT EXISTS narrative_metric_definitions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        metric_id VARCHAR(50) UNIQUE NOT NULL,
        display_name VARCHAR(100) NOT NULL,
        description TEXT,
        rubric_text TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """

    # スコア保存テーブルの作成
    metrics_table_sql = """
    CREATE TABLE IF NOT EXISTS narrative_metrics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        episode_num INTEGER NOT NULL,
        scene_num INTEGER NOT NULL,
        metric_name VARCHAR(50) NOT NULL,
        score INTEGER NOT NULL,
        reasoning TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """

    # インデックスの作成
    index_sql = """
    CREATE INDEX IF NOT EXISTS ix_narrative_metrics_lookup 
    ON narrative_metrics (book_id, branch_id, episode_num, scene_num);
    """

    try:
        with db_mgr.get_session() as session:
            session.execute(text(definition_table_sql))
            session.execute(text(metrics_table_sql))
            session.execute(text(index_sql))
            session.commit()
            logger.info("Narrative metrics tables and indexes created successfully.")
    except Exception as e:
        logger.error(f"Failed to apply narrative metrics migration: {e}")
        raise

if __name__ == "__main__":
    apply_narrative_metrics_migration()

