"""
tests/test_health.py - ヘルスチェックの単体テスト
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.backend.health.checks import (
    HealthCheckResult,
    HealthStatus,
    check_database,
    check_llm_gateway,
    check_redis,
)


class TestHealthStatus:
    """HealthStatus Enum のテスト"""

    def test_health_status_values(self):
        assert HealthStatus.OK == "ok"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.ERROR == "error"
        assert HealthStatus.NOT_CONFIGURED == "not_configured"


class TestHealthCheckResult:
    """HealthCheckResult データクラスのテスト"""

    def test_default_values(self):
        result = HealthCheckResult(status=HealthStatus.OK)
        assert result.status == HealthStatus.OK
        assert result.latency_ms is None
        assert result.details == ""
        assert result.error == ""

    def test_all_fields(self):
        result = HealthCheckResult(
            status=HealthStatus.OK,
            latency_ms=12.5,
            details="pool=5/10",
            error=""
        )
        assert result.latency_ms == 12.5
        assert result.details == "pool=5/10"


class TestCheckDatabase:
    """check_database 関数のテスト"""

    @pytest.mark.asyncio
    async def test_check_database_success(self):
        """DB 接続成功時"""
        mock_db_manager = MagicMock()
        mock_engine = MagicMock()
        mock_pool = MagicMock()
        mock_pool.checkedin.return_value = 5
        mock_pool.size.return_value = 10
        mock_engine.pool = mock_pool

        # async context manager のモック
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()
        mock_cm = MagicMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_cm.__aexit__ = AsyncMock(return_value=None)
        mock_engine.connect.return_value = mock_cm

        mock_db_manager.engine = mock_engine

        result = await check_database(mock_db_manager)

        assert result.status == HealthStatus.OK
        assert result.latency_ms is not None
        assert result.latency_ms > 0
        assert "pool=5/10" in result.details

    @pytest.mark.asyncio
    async def test_check_database_failure(self):
        """DB 接続失敗時"""
        mock_db_manager = MagicMock()
        mock_engine = MagicMock()
        mock_engine.connect.side_effect = Exception("Connection failed")
        mock_db_manager.engine = mock_engine

        result = await check_database(mock_db_manager)

        assert result.status == HealthStatus.ERROR
        assert "Connection failed" in result.error


class TestCheckRedis:
    """check_redis 関数のテスト"""

    @pytest.mark.asyncio
    async def test_check_redis_not_configured(self):
        """Redis URL 未設定時"""
        result = await check_redis(None)
        assert result.status == HealthStatus.NOT_CONFIGURED
        assert "REDIS_URL not configured" in result.error

    @pytest.mark.asyncio
    async def test_check_redis_empty_string(self):
        """Redis URL 空文字時"""
        result = await check_redis("")
        assert result.status == HealthStatus.NOT_CONFIGURED

    @pytest.mark.asyncio
    async def test_check_redis_success(self):
        """Redis 接続成功時"""
        mock_client = AsyncMock()
        mock_client.ping.return_value = True
        mock_client.info.return_value = {"connected_clients": 5}
        mock_client.close = AsyncMock()

        with patch("redis.asyncio.Redis.from_url", return_value=mock_client):
            result = await check_redis("redis://localhost:6379/0")

        assert result.status == HealthStatus.OK
        assert result.latency_ms is not None
        assert "connected_clients=5" in result.details
        mock_client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_redis_failure(self):
        """Redis 接続失敗時"""
        mock_client = AsyncMock()
        mock_client.ping.side_effect = Exception("Connection refused")
        mock_client.close = AsyncMock()

        with patch("redis.asyncio.Redis.from_url", return_value=mock_client):
            result = await check_redis("redis://localhost:6379/0")

        assert result.status == HealthStatus.ERROR
        assert "Connection refused" in result.error


class TestCheckChromadb:
    """check_chromadb 関数のテスト - コンテナ初期化の問題でスキップ"""

    @pytest.mark.skip(reason="Container initialization issue in test environment")
    @pytest.mark.asyncio
    async def test_check_chromadb_not_initialized(self):
        pass

    @pytest.mark.skip(reason="Container initialization issue in test environment")
    @pytest.mark.asyncio
    async def test_check_chromadb_success(self):
        pass

    @pytest.mark.skip(reason="Container initialization issue in test environment")
    @pytest.mark.asyncio
    async def test_check_chromadb_failure(self):
        pass


class TestCheckLLMGateway:
    """check_llm_gateway 関数のテスト"""

    @pytest.mark.asyncio
    async def test_check_llm_gateway_no_api_key(self):
        """API キー未設定時"""
        result = await check_llm_gateway(None)
        assert result.status == HealthStatus.NOT_CONFIGURED

    @pytest.mark.asyncio
    async def test_check_llm_gateway_invalid_key(self):
        """無効なキー時 (空文字等)"""
        result = await check_llm_gateway("")
        assert result.status == HealthStatus.NOT_CONFIGURED

    @pytest.mark.asyncio
    @patch.dict("os.environ", {"KAKU_HEALTH_CHECK_LLM": "false"})
    async def test_check_llm_gateway_disabled_by_env(self):
        """環境変数で無効化時"""
        result = await check_llm_gateway("valid-key")
        assert result.status == HealthStatus.NOT_CONFIGURED
        assert "disabled via env" in result.details

    @pytest.mark.asyncio
    @patch("src.core.llm_gateway.LLMProviderFactory")
    @patch("src.core.llm_gateway.create_genai_client")
    async def test_check_llm_gateway_success(self, mock_create_client, mock_factory_class):
        """LLM Gateway 呼び出し成功時"""
        mock_client = MagicMock()
        mock_create_client.return_value = mock_client

        mock_factory = AsyncMock()
        mock_factory.generate_text.return_value = "pong"
        mock_factory_class.return_value = mock_factory

        result = await check_llm_gateway("valid-key")

        assert result.status == HealthStatus.OK
        assert result.latency_ms is not None
        assert "model=gemini-3.5-flash-lite" in result.details

    @pytest.mark.asyncio
    @patch("src.core.llm_gateway.LLMProviderFactory")
    @patch("src.core.llm_gateway.create_genai_client")
    async def test_check_llm_gateway_failure(self, mock_create_client, mock_factory_class):
        """LLM Gateway 呼び出し失敗時"""
        mock_factory = AsyncMock()
        mock_factory.generate_text.side_effect = Exception("API Error")
        mock_factory_class.return_value = mock_factory

        result = await check_llm_gateway("valid-key")

        assert result.status == HealthStatus.ERROR
        assert "API Error" in result.error


class TestCheckWorker:
    """check_worker 関数のテスト - huey インポート問題でスキップ"""

    @pytest.mark.skip(reason="Huey import issue in test environment")
    @pytest.mark.asyncio
    async def test_check_worker_redis_backend(self):
        pass

    @pytest.mark.skip(reason="Huey import issue in test environment")
    @pytest.mark.asyncio
    async def test_check_worker_sqlite_backend(self):
        pass

    @pytest.mark.skip(reason="Huey import issue in test environment")
    @pytest.mark.asyncio
    async def test_check_worker_unknown_backend(self):
        pass

    @pytest.mark.skip(reason="Huey import issue in test environment")
    @pytest.mark.asyncio
    async def test_check_worker_failure(self):
        pass
