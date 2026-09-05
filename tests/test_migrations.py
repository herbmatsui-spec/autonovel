"""データベースマイグレーション契約テスト.

全マイグレーションが適用・ロールバック可能か、スキーマが期待通りか検証。
"""
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_alembic_config_loads():
    """alembic.ini が正しく読み込める"""
    alembic_cfg = Config("alembic.ini")
    assert alembic_cfg.get_main_option("script_location") == "src/backend/alembic"


def test_migrations_up_down(sqlite_db_url):
    """SQLite 環境で全マイグレーションが適用・ロールバック可能"""
    engine = create_engine(sqlite_db_url)
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", sqlite_db_url)

    # SQLAlchemy モデルからテーブルを作成（初期スキーマ）
    from src.infrastructure.database.models.base_orm import Base
    import src.backend.database.models  # noqa
    import src.infrastructure.database.models  # noqa

    Base.metadata.create_all(engine)

    # ヘッドまで適用
    command.upgrade(alembic_cfg, "head")

    # 主要テーブル存在確認（SQLite では PostgreSQL 専用テーブルは除外）
    inspector = inspect(engine)
    tables = inspector.get_table_names()

    required_tables = [
        "books", "chapters", "characters", "plots",
        "chapter_chunks", "prompt_versions", "bibles", "branches",
        "patch_reviews", "setting_deltas", "setting_versions",
        "multimedia_artifacts", "multimedia_tasks",
        "branch_play_sessions", "publish_records", "book_scores",
    ]
    for table in required_tables:
        assert table in tables, f"Table {table} not found after migration"

    # カラム確認: chapter_chunks.embedding (PostgreSQL のみ)
    # SQLite では embedding カラムは作成されないためスキップ

    # インデックス確認: chapter_chunks
    indexes = inspector.get_indexes("chapter_chunks")
    index_names = [idx["name"] for idx in indexes]
    # pgvector インデックスは PostgreSQL のみだが、SQLite ではスキップされる
    # 少なくとも基本インデックスは存在
    assert any("chapter_id" in name for name in index_names)

    # ベースまでロールバック
    command.downgrade(alembic_cfg, "base")

    # 再度ヘッドまで適用（冪等性確認）
    command.upgrade(alembic_cfg, "head")
    tables_after = inspect(engine).get_table_names()
    for table in required_tables:
        assert table in tables_after


def test_postgres_migrations_if_available(postgres_db_url):
    """PostgreSQL 利用可能なら pgvector/AGE マイグレーションも検証"""
    if not postgres_db_url:
        pytest.skip("PostgreSQL not available")

    engine = create_engine(postgres_db_url)
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", postgres_db_url)

    # ヘッドまで適用
    command.upgrade(alembic_cfg, "head")

    inspector = inspect(engine)

    # pgvector 拡張確認
    with engine.connect() as conn:
        ext_result = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
        assert ext_result.fetchone() is not None, "pgvector extension not installed"

        age_result = conn.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'age'"))
        assert age_result.fetchone() is not None, "AGE extension not installed"

    # AGE グラフ確認
    with engine.connect() as conn:
        conn.execute(text("LOAD 'age';"))
        conn.execute(text('SET search_path = ag_catalog, "$user", public;'))
        graph_result = conn.execute(text("SELECT 1 FROM ag_graph WHERE name = 'autonovel_graph'"))
        assert graph_result.fetchone() is not None, "Default graph not created"

    # HNSW インデックス確認
    columns = inspector.get_columns("chapter_chunks")
    embedding_col = next(c for c in columns if c["name"] == "embedding")
    # PostgreSQL では vector(1536) になっているはず
    assert "vector" in str(embedding_col["type"]).lower()


def test_migration_ordering():
    """マイグレーションバージョン順序が正しい（ダウングレード時エラーにならない）"""
    from alembic.script import ScriptDirectory

    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)

    # walk_revisions("base", "head") は head から base へ向かって降順で返すため、reverse して昇順にする
    revisions = list(script.walk_revisions("base", "head"))
    revisions.reverse()  # base -> head の昇順にする
    assert len(revisions) > 0

    # バージョン順序確認（数値プレフィックス順・昇順）
    version_nums = []
    for rev in revisions:
        try:
            num = int(rev.revision.split("_")[0])
            version_nums.append(num)
        except (ValueError, IndexError):
            pass

    if version_nums:
        assert version_nums == sorted(version_nums), "Migration versions not in order"


def test_no_duplicate_revision_ids():
    """リビジョン ID 重複なし"""
    from alembic.script import ScriptDirectory

    alembic_cfg = Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)

    revision_ids = [rev.revision for rev in script.walk_revisions("base", "head")]
    assert len(revision_ids) == len(set(revision_ids)), "Duplicate revision IDs found"