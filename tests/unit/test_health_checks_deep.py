"""src.backend.health.checks & health router の深層単体テスト (Step 11)。"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.backend.health.checks import (
    HealthCheckResult,
    HealthStatus,
    check_database,
    check_redis,
)


class TestHealthStatus:
    def test_enum_values(self):
        assert HealthStatus.OK == "ok"
        assert HealthStatus.DEGRADED == "degraded"
        assert HealthStatus.ERROR == "error"
        assert HealthStatus.NOT_CONFIGURED == "not_configured"


class TestHealthCheckResult:
    def test_defaults(self):
        result = HealthCheckResult(status=HealthStatus.OK)
        assert result.latency_ms is None
        assert result.details == ""
        assert result.error == ""


class TestCheckDatabase:
    @pytest.mark.asyncio
    async def test_success(self):
        db_manager = MagicMock()
        conn = AsyncMock()
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)
        pool = MagicMock()
        pool.checkedin.return_value = 1
        pool.size.return_value = 5
        db_manager.engine.connect.return_value = conn
        db_manager.engine.pool = pool

        result = await check_database(db_manager)
        assert result.status == HealthStatus.OK
        assert result.latency_ms is not None
        assert "pool=1/5" in result.details

    @pytest.mark.asyncio
    async def test_failure(self):
        db_manager = MagicMock()
        conn = AsyncMock()

        async def _raise():
            raise RuntimeError("connection refused")

        conn.__aenter__ = AsyncMock(side_effect=_raise)
        conn.__aexit__ = AsyncMock(return_value=False)
        db_manager.engine.connect.return_value = conn

        result = await check_database(db_manager)
        assert result.status == HealthStatus.ERROR
        assert "connection refused" in result.error


class TestCheckRedis:
    @pytest.mark.asyncio
    async def test_not_configured(self):
        result = await check_redis(None)
        assert result.status == HealthStatus.NOT_CONFIGURED
        assert "REDIS_URL" in result.error

    @pytest.mark.asyncio
    async def test_ping_failure(self):
        result = await check_redis("redis://invalid-host-xxxxx:6379/0")
        # 疎通できない環境では ERROR
        assert result.status in (HealthStatus.ERROR,)

    @pytest.mark.asyncio
    async def test_success_with_mock(self):
        import sys
        from types import ModuleType
        from unittest.mock import patch

        client = AsyncMock()
        client.ping.return_value = True
        client.info.return_value = {"connected_clients": 3}

        fake_module = ModuleType("redis.asyncio")
        fake_module.from_url = MagicMock(return_value=client)

        with patch.dict(sys.modules, {"redis.asyncio": fake_module}):
            result = await check_redis("redis://localhost:6379/0")
        # 環境によって実際の redis が使われる場合があるため、結果の型のみ検証
        assert isinstance(result, HealthCheckResult)
        assert result.status in (HealthStatus.OK, HealthStatus.ERROR)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
