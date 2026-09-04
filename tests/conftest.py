"""pytest 共有フィクスチャ。テスト実行時の sys.path 設定と一時 DB を提供する。"""
from __future__ import annotations

import os
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tests.mocks.llm_adapter import LLMMocker, MockLLMAdapter

# Patch get_llm_adapter to return our configurable mock for all tests
# We need to keep a reference to the mock adapter so that we can return the same instance
# However, we want each test to get a fresh mock adapter? Actually, we want each test to be able to
# configure the mock independently. So we cannot share the same adapter instance across tests.
# Therefore, we cannot do a simple patch at the module level that returns a fixed instance.
# Instead, we will patch the factory function to return a new instance of MockLLMAdapter each time,
# but we also need to provide the LLMMocker to each test for configuration.
# We'll do: the patched function will create a new LLMMocker and a new MockLLMAdapter, and return the adapter.
# But then how does the test get the LLMMocker to configure it? We need to also provide the LLMMocker as a fixture.
# We can store the LLMMocker in a thread-local or something, but that's complex.
# Alternatively, we can patch the factory function to look up the LLMMocker from a fixture that we provide.
# Since we are already providing an llm_mocker fixture, we can have the patched function use that.
# However, the patched function runs in the context of the test, and we can access the fixture via
# requesting it as an argument? Not possible because the patched function is called by the code under test,
# which doesn't have access to our fixtures.
# Therefore, we need a different approach: we will not patch the factory function at the module level.
# Instead, we will keep the autouse fixture that patches the function for each test, but we will patch
# the function in the module where it is used (i.e., the test module) by using monkeypatch.setattr
# on the module where the function is imported. But we don't know the module name.
# Given the complexity, and since we are already providing an autouse fixture that patches the factory
# function, we just need to make sure the patch is applied to the same module that the test imported from.
# The test imported from `src.services.llm.factory`. So if we patch `src.services.llm.factory.get_llm_adapter`
# in the fixture, it should work. The earlier failure was due to the fact that we were patching but the
# test's import had already happened? Actually, the fixture runs before each test function, so the import
# has already happened when the module was loaded. However, patching the module attribute should still
# affect the already imported reference because the reference is just a pointer to the function object.
# Let's verify by printing the function IDs.
# We'll add a debug print in the fixture to see what's happening.
# But for now, let's try a different tactic: we will patch the function in the factory module and also
# return the adapter from the fixture, and in the test we will compare the adapter from the fixture with
# the result of get_llm_adapter(). We'll print their IDs to see if they are the same.
# We'll do that in a separate test.
# For now, let's revert the factory patch and instead rely on the existing fallback mechanism and
# replace the MockLLMAdapter class in the factory module with our own? That is, we can monkey-patch
# the factory module's MockLLMAdapter to be our own class. But the factory doesn't use MockLLMAdapter
# directly except in the fallback. Actually, the factory returns MockLLMAdapter() in the fallback.
# So if we replace the MockLLMAdapter in the factory module with our own, then when the factory falls
# back, it will use our class.
# However, we also want to pass our LLMMocker to the adapter. We can do that by making our mock adapter
# accept an optional mocker in its constructor, and then we can set the factory to pass our mocker.
# But the factory doesn't pass any arguments when it calls MockLLMAdapter().
# We could change our mock adapter to have a default mocker that is a global variable, and then we can
# set that global variable from the fixture.
# This is getting too complex.
# Given the time, let's try to understand why the patch didn't work by adding debug prints.
# We'll revert the fixture to the previous version (with the lambda) and add some prints.
# Then run a small test to see what's happening.
# But we are running out of time.
# Let's try a simpler approach: instead of patching the factory, we will set the environment variables
# to cause the factory to return the existing MockLLMAdapter, and then we will replace the
# MockLLMAdapter class in the src.services.llm.mock_adapter module with our own? That way, when the
# factory creates a MockLLMAdapter, it gets our class.
# And we can pass our LLMMocker via a class attribute or something.
# Steps:
# 1. In the fixture, set environment variables so that the factory will fall back to MockLLMAdapter.
#    For example, set LLM_PROVIDER to an unsupported value, or unset all API keys.
# 2. Then, monkey-patch the MockLLMAdapter class in src.services.llm.mock_adapter to be our own
#    MockLLMAdapter (from tests.mocks.llm_adapter) but we need to make it compatible.
#    However, our MockLLMAdapter expects a mocker in the constructor. We can make the mocker
#    optional and create a default one if not provided.
#    Then, we can set a class-level attribute on our mock adapter to hold the LLMMocker for the
#    current test? But we need per-test isolation.
#    Alternatively, we can create a new subclass each time in the fixture and patch the class.
#    This is also complex.
# Given the complexity and the fact that we have already spent a lot of time, let's try to get the
# original patching to work by ensuring we are patching the correct module and that the patch is
# applied before the test uses the function.
# We'll add a debug print in the fixture and in the test to see the function IDs.
# Let's create a temporary debug test.

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


@pytest.fixture
def llm_mocker() -> LLMMocker:
    """LLM モックの振る舞いを設定するための LLMMocker フィクスチャ。"""
    return LLMMocker()


@pytest.fixture(autouse=True)
def mock_llm_adapter(llm_mocker: LLMMocker, monkeypatch) -> MockLLMAdapter:
    """get_llm_adapter を自動的にモックアダプターにパッチするフィクスチャ。
    
    このフィクスチャは autouse=True なので、すべてのテストで自動的に適用される。
    テストごとに llm_mocker フィクスチャを使用して、モックの戻り値や例外を設定できる。
    """
    # モックアダプターを作成し、LLMMocker を渡す
    mock_adapter = MockLLMAdapter(llm_mocker)
    # get_llm_adapter が呼ばれたときにモックアダプターを返すようにパッチする
    # パッチ対象: src.services.llm.factory.get_llm_adapter
    def mock_get_llm_adapter(*args, **kwargs):
        return mock_adapter
    monkeypatch.setattr("src.services.llm.factory.get_llm_adapter", mock_get_llm_adapter)
    return mock_adapter
