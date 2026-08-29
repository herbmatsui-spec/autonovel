import os
import sys
import tempfile
from pathlib import Path

import pytest
from src.backend.database import UnitOfWork

# Set test environment for database init
os.environ.setdefault("KAKU_ENV", "test")
os.environ.setdefault("ENVIRONMENT", "test")

# 動的パス解決: プロジェクトルートおよびサブパッケージを sys.path に追加
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
WORKSPACE_ROOT = PROJECT_ROOT.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

try:
    from sqlalchemy import create_engine

    from src.backend.database.core import DatabaseManager
    from src.backend.database.models import Base

    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    create_engine = None
    DatabaseManager = None
    Base = None


@pytest.fixture
def real_db_manager():
    """
    実際の SQLite データベース管理器を提供する。
    FullAutoWorkflow のテストに使用される。
    """
    if not HAS_SQLALCHEMY:
        pytest.skip("sqlalchemy モジュールが利用できないためスキップします")

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    db_path = Path(tmp.name)
    db_url = f"sqlite+aiosqlite:///{db_path}"

    # スキーマ構築（同期エンジン）
    sync_url = f"sqlite:///{db_path}"
    engine = create_engine(sync_url)
    Base.metadata.create_all(engine)
    engine.dispose()

    manager = DatabaseManager(db_url)
    yield manager


    try:
        db_path.unlink()
    except OSError:
        pass

@pytest.fixture
def real_uow(real_db_manager):
    return UnitOfWork(real_db_manager)


@pytest.fixture
def mock_llm():
    from tests.mocks.mock_llm import MockGeminiApiClient
    return MockGeminiApiClient()

# ---------------------------------------------------------------------------
# RedisCacheService のテスト用モック
# ---------------------------------------------------------------------------
from unittest.mock import AsyncMock

class MockRedisCacheService:
    """RedisCacheService の簡易モック。
    すべてのメソッドは AsyncMock を利用し、実際の Redis 接続は行わない。
    必要に応じて属性や戻り値を個別テストで設定できる。
    """
    def __init__(self, *args, **kwargs):
        self._client = AsyncMock()
        self._pool = None

# pytest の自動適用 (autouse) で全テストに適用
@pytest.fixture(autouse=True)
def mock_redis_service(monkeypatch):
    monkeypatch.setattr('src.services.redis_cache.RedisCacheService', MockRedisCacheService)
    return MockRedisCacheService
    """
    統合テスト用の LLM モックを提供する。
    MockGeminiApiClient インスタンスを返し、レスポンスを事前定義できる。
    """
    from tests.mocks.mock_llm import MockGeminiApiClient

    return MockGeminiApiClient()
