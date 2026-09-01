"""SQLAlchemy engine と SessionLocal を初期化するデータベース設定モジュール。"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from src.backend.config import settings
from src.backend.logging_config import get_logger
from src.models import Base

logger = get_logger("database")

# settings から DATABASE_URL を取得
DATABASE_URL = settings.DATABASE_URL

# SQLite の場合は check_same_thread=False が必要
engine_args = {}
if DATABASE_URL.startswith("sqlite"):
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_args)

# PostgreSQL かつ GraphRAG 有効時は AGE のロードを自動実行
if DATABASE_URL.startswith("postgresql") and settings.ENABLE_GRAPHRAG:
    @event.listens_for(engine, "connect")
    def on_connect(dbapi_con, connection_record):
        try:
            cursor = dbapi_con.cursor()
            cursor.execute("LOAD 'age';")
            cursor.execute('SET search_path = ag_catalog, "$user", public;')
            cursor.close()
        except Exception as e:
            logger.warning("Could not initialize Apache AGE on connection: %s", e)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依存注入用の DB セッションジェネレーター"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """データベースのテーブルを初期化する"""
    Base.metadata.create_all(bind=engine)
    if DATABASE_URL.startswith("postgresql") and settings.ENABLE_GRAPHRAG:
        with engine.begin() as conn:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS age;"))
                conn.execute(text("LOAD 'age';"))
                conn.execute(text('SET search_path = ag_catalog, "$user", public;'))
                # 初期グラフの作成（存在しない場合のみ）
                graph_name = settings.AGE_GRAPH_NAME
                conn.execute(text(f"SELECT create_graph('{graph_name}');"))
                logger.info("GraphRAG (pgvector + Apache AGE) initialized successfully.")
            except Exception as e:
                logger.warning("Could not auto-initialize AGE/pgvector extensions: %s", e)


__all__: list[str] = [
    "Base",
    "DATABASE_URL",
    "SessionLocal",
    "engine",
    "get_db",
    "init_db",
]
