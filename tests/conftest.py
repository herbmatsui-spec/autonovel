"""pytest 共有フィクスチャ。テスト実行時の sys.path 設定と一時 DB を提供する。"""
from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path

def pytest_configure(config):
    """Set environment variables before test collection."""
    os.environ.setdefault("APP_ENV", "testing")
    # Monkeypatch init_db to prevent premature table creation during app import
    def dummy_init_db(*args, **kwargs):
        pass
    try:
        import src.backend.server
        src.backend.server.init_db = dummy_init_db
    except Exception:
        pass

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

CHROMADB_AVAILABLE = False
try:
    import chromadb
    CHROMADB_AVAILABLE = True
except Exception:
    CHROMADB_AVAILABLE = False

RANK_BM25_AVAILABLE = False
try:
    import rank_bm25
    RANK_BM25_AVAILABLE = True
except Exception:
    RANK_BM25_AVAILABLE = False

PGVECTOR_AVAILABLE = False
try:
    import importlib.util

    if importlib.util.find_spec("pgvector") is not None:
        PGVECTOR_AVAILABLE = True
    if os.environ.get("AUTONOVEL_FORCE_PGVECTOR", "1") != "1":
        PGVECTOR_AVAILABLE = False
except Exception:
    PGVECTOR_AVAILABLE = False

REDIS_AVAILABLE = False
try:
    import redis.asyncio as redis

    async def _check_redis():
        try:
            client = redis.Redis(host="localhost", port=6379, socket_connect_timeout=1)
            await client.ping()
            await client.close()
            return True
        except Exception:
            return False

    import asyncio

    REDIS_AVAILABLE = asyncio.run(_check_redis())
except Exception:
    REDIS_AVAILABLE = False

GEMINI_AVAILABLE = False
try:
    import google.generativeai

    GEMINI_AVAILABLE = True
except Exception:
    GEMINI_AVAILABLE = False


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

@pytest.fixture
def real_db_manager(monkeypatch) -> Generator[Session, None, None]:
    """
    実際の SQLite 一時データベース管理器を提供する。
    統合テスト・ワークフローテストに使用される。

    ``DATABASE_URL`` を一時ファイル経由で差し替え、``init_db()`` でスキーマ生成後に
    有効な ``Session`` を ``yield`` する。終了時にファイルを削除する。
    """
    from sqlalchemy.orm import sessionmaker

    import src.backend.database as db_module
    import src.backend.database.core as db_core
    from src.backend.database import SessionLocal, engine, init_db

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = Path(tmp.name)

    test_url = f"sqlite:///{db_path}"
    previous_url = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = test_url

    # core.py のグローバル変数も更新（プロキシが参照するため）
    import sys
    db_core.DATABASE_URL = test_url
    db_core._sync_engine = None
    db_core._sync_session_factory = None

    # 同一プロセス内で module の engine/SessionLocal を差し替える
    test_engine = create_engine(test_url, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db_module.engine = test_engine
    db_module.SessionLocal = TestSessionLocal  # type: ignore[assignment]

    # モデル定義から全テーブル作成（最新スキーマ反映）
    from src.backend.database.models import Base as BackendBase
    from src.infrastructure.database.models import Base as InfraBase
    InfraBase.metadata.create_all(test_engine)
    BackendBase.metadata.create_all(test_engine)

    # init_db をモンキーパッチして、二重初期化を防ぐ
    def dummy_init_db(*args, **kwargs):
        pass
    monkeypatch.setattr(db_module, "init_db", dummy_init_db)
    monkeypatch.setattr(db_core, "init_db", dummy_init_db)

    session = TestSessionLocal()
    try:
        yield session
    finally:
        import gc

        try:
            session.rollback()
        except Exception:
            pass
        session.close()

        test_engine.dispose()
        gc.collect()
        # 元の状態に戻す
        db_module.engine = engine
        db_module.SessionLocal = SessionLocal  # type: ignore[assignment]
        db_core.DATABASE_URL = previous_url or (db_core.settings.DATABASE_URL if hasattr(db_core, 'settings') else "sqlite:///storage/autonovel.db")
        db_core._sync_engine = None
        db_core._sync_session_factory = None
        if previous_url is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = previous_url
        try:
            if db_path.exists():
                db_path.unlink()
        except OSError:
            pass


@pytest.fixture
def db_session(real_db_manager: Generator[Session, None, None]) -> Generator[Session, None, None]:
    """テスト用 DB セッションフィクスチャ (real_db_manager のエイリアス)."""
    return real_db_manager


@pytest.fixture
def sqlite_db_url(tmp_path) -> str:
    """SQLite テスト用の一時データベース URL を返す。"""
    db_path = tmp_path / "test_migrations.db"
    return f"sqlite:///{db_path}"


@pytest.fixture
def postgres_db_url() -> str | None:
    """PostgreSQL テスト用のデータベース URL を返す（環境変数未設定なら None）。"""
    return os.environ.get("POSTGRES_TEST_URL")


@pytest.fixture
def tmp_chroma_path(tmp_path):
    """Chromadb 用の一時ディレクトリパスを返す."""
    p = tmp_path / "chroma"
    p.mkdir()
    return str(p)


@pytest.fixture(autouse=True)
def reset_metrics():
    """各テスト後に health.py のプロセスメトリクスをゼロリセットする。

    pytest-xdist 並列実行時にメトリクスがリークするのを防止する。
    """
    from src.backend.observability.health import metrics

    yield
    metrics.reset_for_testing()


@pytest.fixture
def client(db_session: Session):
    """FastAPI TestClient フィクスチャ."""
    from fastapi.testclient import TestClient

    from src.backend import database
    from src.backend.server import app

    app.dependency_overrides[database.get_db] = lambda: db_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
