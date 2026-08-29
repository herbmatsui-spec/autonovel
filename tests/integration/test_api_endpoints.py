#!/usr/bin/env python3
"""
API エンドポイント統合テスト

SQLite + モック Redis/LLM でのエンドポイントテスト (testcontainers 不要)
"""

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mock_llm_proxy():
    """モック LLM プロキシ"""
    mock = MagicMock()
    mock.generate_json = AsyncMock(return_value=MagicMock(
        success=True,
        content={"plot": "テストプロット", "scenes": []},
        metadata={},
        token_usage={"prompt": 100, "completion": 200, "calls": 1}
    ))
    mock.generate_text = AsyncMock(return_value=MagicMock(
        success=True,
        content="生成された本文です。" * 10,
        metadata={},
        token_usage={"prompt": 50, "completion": 150, "calls": 1}
    ))
    return mock


@pytest.fixture
def mock_huey():
    """モック Huey タスクキュー"""
    with patch("src.backend.tasks.execute_easy_mode_generation") as mock_task:
        mock_task.delay = MagicMock(return_value=MagicMock())
        yield mock_task.delay


@pytest.fixture
def mock_redis():
    """モック Redis クライアント"""
    with patch("redis.asyncio.Redis") as mock_redis_class:
        mock_redis = MagicMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.eval = AsyncMock(return_value=1)
        mock_redis_class.return_value = mock_redis
        yield mock_redis


@pytest.fixture
def chromadb_container():
    """ChromaDB コンテナをモックで置き換え"""
    mock = MagicMock()
    mock.get_container_host_ip.return_value = "localhost"
    mock.get_exposed_port.return_value = 8000
    return mock


@pytest.fixture
def app_with_mocks(db_manager, mock_llm_proxy, mock_huey, mock_redis, monkeypatch):
    """モックを注入した FastAPI アプリ"""
    from src.core.container import AppContainer
    from src.backend.server import app as original_app
    
    # 環境変数をテスト用に設定
    monkeypatch.setenv("KAKU_DATABASE_URL", str(db_manager.engine.url))
    monkeypatch.setenv("KAKU_REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("KAKU_GEMINI_API_KEY", "test-key")
    monkeypatch.setenv("KAKU_FAIL_FAST_MODE", "true")
    # レートリミットをフェイルオープンにして Redis 不要にする
    monkeypatch.setenv("RATE_LIMIT_FAIL_OPEN", "true")
    
    # コンテナをリセットしてモックを注入
    container = AppContainer()
    container.llm.override(mock_llm_proxy)
    container.db.override(db_manager)
    
    # 元のアプリのコンテナを置き換え
    original_app.state.container = container
    
    # レートリミッターをモックで無効化
    import src.backend.server as server_module
    mock_limiter = MagicMock()
    mock_limiter.is_allowed = AsyncMock(return_value=True)
    server_module._redis_rate_limiter = mock_limiter
    
    return original_app


@pytest_asyncio.fixture
async def async_client(app_with_mocks):
    """非同期テストクライアント"""
    transport = ASGITransport(app=app_with_mocks)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


class TestEasyModeGenerateEndpoint:
    """/api/easy_mode/generate エンドポイントのテスト"""

    @pytest.mark.asyncio
    async def test_generate_success(self, async_client, mock_huey):
        """正常な生成リクエストで 200 と task_id が返る"""
        payload = {
            "genre": "fantasy",
            "keywords": "魔法,冒険",  # カンマ区切り文字列
            "archetype_key": "banished_strongest",
            "target_eps": 5,
            "initial_limit": 3,
            "word_count": 2000,
            "concept": "追放された最強の魔法使い",
            "tone_vibe": 0.8,  # float
            "style_key": "web_novel",
            "enable_erotic": False,
            "erotic_intensity": 0,
            "config": {},
        }
        
        response = await async_client.post(
            "/api/easy_mode/generate",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "task_id" in data["data"]
        assert data["message"] == "かんたんモード生成を開始しました"
        mock_huey.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_validation_error(self, async_client):
        """必須フィールド欠如で 422 が返る"""
        payload = {
            "genre": "fantasy",
            # keywords 欠如
            "target_eps": 5,
        }
        
        response = await async_client.post(
            "/api/easy_mode/generate",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_generate_invalid_type(self, async_client):
        """型不正で 422 が返る"""
        payload = {
            "genre": "fantasy",
            "keywords": ["魔法"],
            "target_eps": "not_an_int",
        }
        
        response = await async_client.post(
            "/api/easy_mode/generate",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422


class TestRefineEroticEndpoint:
    """/api/refine_erotic エンドポイントのテスト"""

    @pytest.mark.asyncio
    async def test_refine_success(self, async_client):
        """正常なリクエストで 200 が返る"""
        with patch("src.backend.tasks.execute_service_workflow") as mock_task:
            mock_task.delay = MagicMock(return_value=MagicMock())
            
            payload = {
                "book_id": 1,
                "ep_num": 1,
                "intensity": 5,
                "platform_preset": "kindle",
                "config": {},
            }
            
            response = await async_client.post(
                "/api/refine_erotic",
                json=payload,
                headers={"X-API-Key": "test-key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "task_id" in data["data"]
            assert data["message"] == "官能表現の洗練を開始しました"
            mock_task.delay.assert_called_once()

    @pytest.mark.asyncio
    async def test_refine_validation_error(self, async_client):
        """必須フィールド欠如で 422"""
        payload = {
            "book_id": 1,
            # ep_num 欠如
        }
        
        response = await async_client.post(
            "/api/refine_erotic",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 422


class TestCritiqueOptimizeEndpoint:
    """/api/critique/optimize エンドポイントのテスト"""

    @pytest.mark.asyncio
    async def test_optimize_success(self, async_client):
        """正常なリクエストで 200 が返る"""
        with patch("src.backend.tasks.execute_service_workflow") as mock_task:
            mock_task.delay = MagicMock(return_value=MagicMock())
            
            payload = {
                "book_id": 1,
                "config": {},
            }
            
            response = await async_client.post(
                "/api/critique/optimize",
                json=payload,
                headers={"X-API-Key": "test-key"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "task_id" in data["data"]
            assert data["message"] == "品質分析を開始しました"
            mock_task.delay.assert_called_once()


class TestAuthErrors:
    """認証エラーのテスト"""

    @pytest.mark.asyncio
    async def test_missing_api_key(self, async_client):
        """API キーなしで 401/403"""
        payload = {"genre": "fantasy", "keywords": ["魔法"], "target_eps": 5}
        
        response = await async_client.post(
            "/api/easy_mode/generate",
            json=payload
            # X-API-Key なし
        )
        
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_invalid_api_key(self, async_client):
        """無効な API キーで 401/403"""
        payload = {"genre": "fantasy", "keywords": ["魔法"], "target_eps": 5}
        
        response = await async_client.post(
            "/api/easy_mode/generate",
            json=payload,
            headers={"X-API-Key": "invalid-key"}
        )
        
        assert response.status_code in (401, 403)


class TestRateLimiting:
    """レートリミットのテスト"""

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self, async_client, monkeypatch):
        """閾値以上のリクエストで 429"""
        # 低い閾値に設定
        monkeypatch.setenv("KAKU_RATE_LIMIT_MAX_REQUESTS", "2")
        monkeypatch.setenv("KAKU_RATE_LIMIT_WINDOW_SECONDS", "60")
        
        # 有効な API キーでテスト（認証エラーを避けるため）
        payload = {"genre": "fantasy", "keywords": "魔法", "target_eps": 5}
        headers = {"X-API-Key": "test-key"}
        
        # レートリミッターをモックで制御
        import src.backend.server as server_module
        call_count = [0]
        async def mock_is_allowed(*args, **kwargs):
            call_count[0] += 1
            return call_count[0] <= 2
        
        original_limiter = server_module._redis_rate_limiter
        mock_limiter = MagicMock()
        mock_limiter.is_allowed = mock_is_allowed
        server_module._redis_rate_limiter = mock_limiter
        
        try:
            # 最初の2回は成功
            r1 = await async_client.post("/api/easy_mode/generate", json=payload, headers=headers)
            r2 = await async_client.post("/api/easy_mode/generate", json=payload, headers=headers)
            # 3回目で制限
            r3 = await async_client.post("/api/easy_mode/generate", json=payload, headers=headers)
            
            # いずれかが 429 になることを確認
            statuses = [r1.status_code, r2.status_code, r3.status_code]
            assert 429 in statuses
        finally:
            server_module._redis_rate_limiter = original_limiter


class TestHealthEndpoint:
    """ヘルスチェックエンドポイント"""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client):
        """ヘルスチェックが 200 を返す"""
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # ヘルスチェックは status フィールドを持つ
        assert "status" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])