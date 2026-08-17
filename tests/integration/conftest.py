"""
Testcontainers integration test configuration.
Provides PostgreSQL, Redis, and ChromaDB containers for integration tests.
"""

import os
import pytest
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.redis import RedisContainer
from testcontainers.core.generic import DockerContainer

# ===================== コンテナフィクスチャ =====================

@pytest.fixture(scope="session")
def postgres_container():
    """PostgreSQL コンテナ (セッションスコープで共有)"""
    container = PostgresContainer(
        image="postgres:16-alpine",
        username="test",
        password="test",
        dbname="test_autonovel",
        port=5432,
    )
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def redis_container():
    """Redis コンテナ (セッションスコープで共有)"""
    container = RedisContainer(image="redis:7-alpine", port=6379)
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def chromadb_container():
    """ChromaDB コンテナ (セッションスコープで共有)"""
    container = DockerContainer(
        image="chromadb/chroma:0.4.22",
        env={"CHROMA_SERVER_HOST": "0.0.0.0", "CHROMA_SERVER_HTTP_PORT": "8000"},
    )
    container.with_exposed_ports(8000)
    container.start()
    yield container
    container.stop()


# ===================== 環境変数オーバーライド =====================

@pytest.fixture(autouse=True, scope="function")
def override_settings(postgres_container, redis_container, chromadb_container, monkeypatch):
    """各テストで設定をコンテナ接続情報にオーバーライド"""
    # PostgreSQL
    pg_url = postgres_container.get_connection_url()
    # asyncpg 用に変換
    pg_url = pg_url.replace("postgresql://", "postgresql+asyncpg://")
    monkeypatch.setenv("KAKU_DATABASE_URL", pg_url)
    monkeypatch.setenv("DATABASE_URL", pg_url)

    # Redis
    redis_host = redis_container.get_container_host_ip()
    redis_port = redis_container.get_exposed_port(6379)
    redis_url = f"redis://{redis_host}:{redis_port}/0"
    monkeypatch.setenv("KAKU_REDIS_URL", redis_url)
    monkeypatch.setenv("REDIS_URL", redis_url)

    # ChromaDB
    chroma_host = chromadb_container.get_container_host_ip()
    chroma_port = chromadb_container.get_exposed_port(8000)
    chroma_url = f"http://{chroma_host}:{chroma_port}"
    monkeypatch.setenv("KAKU_CHROMA_URL", chroma_url)

    # テスト用設定
    monkeypatch.setenv("KAKU_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("KAKU_FAIL_FAST_MODE", "true")
    monkeypatch.setenv("KAKU_MAX_CONCURRENT_API_CALLS", "2")
    monkeypatch.setenv("KAKU_GEMINI_API_KEY", "test-key")  # モック用

    yield
    # クリーンアップ (必要に応じて)


# ===================== データベース初期化ヘルパー =====================

@pytest.fixture
async def db_manager(postgres_container):
    """初期化済み DatabaseManager インスタンス"""
    from sqlalchemy.ext.asyncio import create_async_engine
    from src.backend.database.core import DatabaseManager

    pg_url = postgres_container.get_connection_url().replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(pg_url, echo=False)

    # テーブル作成
    async with engine.begin() as conn:
        # 基本テーブル作成 (models からメタデータ取得)
        from src.models.base import Base
        await conn.run_sync(Base.metadata.create_all)

    manager = DatabaseManager(engine=engine)
    yield manager
    await engine.dispose()


# ===================== ChromaDB クライアント =====================

@pytest.fixture
def chroma_client(chromadb_container):
    """ChromaDB クライアント"""
    import chromadb
    chroma_host = chromadb_container.get_container_host_ip()
    chroma_port = chromadb_container.get_exposed_port(8000)
    client = chromadb.HttpClient(host=chroma_host, port=chroma_port)
    yield client
    # クリーンアップ: 全コレクション削除
    for col in client.list_collections():
        client.delete_collection(col.name)


# ===================== Redis クライアント =====================

@pytest.fixture
def redis_client(redis_container):
    """Redis クライアント"""
    import redis.asyncio as redis
    redis_host = redis_container.get_container_host_ip()
    redis_port = redis_container.get_exposed_port(6379)
    client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
    yield client
    client.close()


# ===================== テスト用モック LLM =====================

@pytest.fixture
def mock_llm_client():
    """モック LLM クライアント (テスト用)"""
    from unittest.mock import AsyncMock, MagicMock
    from src.core.llm_clients.base import BaseLLMClient

    mock = MagicMock(spec=BaseLLMClient)
    mock.generate_json = AsyncMock(return_value=(
        {"success": True, "content": "test bible"},
        "test content",
        {"prompt_tokens": 100, "completion_tokens": 200}
    ))
    mock.generate_text = AsyncMock(return_value=(
        "test generated content",
        {"prompt_tokens": 50, "completion_tokens": 150}
    ))
    return mock


# ===================== テスト用エンジン =====================

@pytest.fixture
async def test_engine(db_manager, mock_llm_client, monkeypatch):
    """テスト用エンジンインスタンス"""
    from src.core.container import AppContainer
    from src.core.llm_gateway import LLMGenerateResultProxy

    container = AppContainer()
    container.config.override({"database_url": db_manager.engine.url})

    # LLM ゲートウェイをモックで置き換え
    mock_proxy = MagicMock()
    mock_proxy.generate_json = mock_llm_client.generate_json
    mock_proxy.generate_text = mock_llm_client.generate_text
    mock_proxy.get_client = mock_llm_client

    container.llm.override(mock_proxy)

    engine = container.engine()
    yield engine
    engine.dispose()


# ===================== ユーティリティ =====================

@pytest.fixture
def sample_bible():
    """サンプル Bible データ"""
    return {
        "world": {"name": "テスト世界", "magic_system": "スキルベース"},
        "protagonist": {"name": "テスト主人公", "archetype": "追放された最強"},
        "cheat_ability": "全スキル習得",
        "catharsis_target": "元パーティ",
        "plot_keys": {"humiliation_ep": 2, "trigger_ep": 3, "musou_start_ep": 4, "final_ep": 8}
    }


@pytest.fixture
def sample_episode_content():
    """サンプル エピソードコンテンツ"""
    return "ざまぁ見ろ。実はチートだった。圧倒的無双で完全制圧だ。"


# ===================== pytest 設定 =====================

def pytest_configure(config):
    """pytest 設定"""
    config.addinivalue_line("markers", "integration: 統合テスト (コンテナ必要)")
    config.addinivalue_line("markers", "slow: 低速テスト")
    config.addinivalue_line("markers", "e2e: E2E テスト")


def pytest_collection_modifyitems(config, items):
    """テストアイテム修正"""
    # integration マーカーがないテストはデフォルトで unit 扱い
    for item in items:
        if "integration" not in item.keywords and "e2e" not in item.keywords:
            item.add_marker(pytest.mark.unit)
