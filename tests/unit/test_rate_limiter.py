"""RedisRateLimiter のフェイルクローズ動作テスト"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.backend.rate_limit import RedisRateLimiter, RATE_LIMIT_FAIL_OPEN


class MockRedisCacheService:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    async def eval(self, script, keys, args):
        if self.should_fail:
            return None
        return 1


@pytest.mark.asyncio
async def test_rate_limiter_fail_close_on_redis_error(monkeypatch):
    """Redis がエラーを返した場合、フェイルクローズ設定时会話を拒否する"""
    redis = MockRedisCacheService(should_fail=True)
    limiter = RedisRateLimiter(
        redis=redis,
        max_requests=100,
        window_seconds=60,
        fail_open=False,
    )
    result = await limiter.is_allowed("test_client")
    assert result is False


@pytest.mark.asyncio
async def test_rate_limiter_fail_open_on_redis_error_when_enabled(monkeypatch):
    """Redis がエラーを返した場合でも fail_open=True ならリクエストを許可する"""
    redis = MockRedisCacheService(should_fail=True)
    limiter = RedisRateLimiter(
        redis=redis,
        max_requests=100,
        window_seconds=60,
        fail_open=True,
    )
    result = await limiter.is_allowed("test_client")
    assert result is True


@pytest.mark.asyncio
async def test_rate_limiter_allows_request_when_under_limit(monkeypatch):
    """通常時（Redis 正常）はリクエストを許可する"""
    redis = MockRedisCacheService(should_fail=False)
    limiter = RedisRateLimiter(
        redis=redis,
        max_requests=100,
        window_seconds=60,
        fail_open=False,
    )
    result = await limiter.is_allowed("test_client")
    assert result is True


@pytest.mark.asyncio
async def test_rate_limiter_rejects_request_when_over_limit(monkeypatch):
    """Redis が 0 を返した場合（レート超過）はリクエストを拒否する"""
    class OverLimitRedis(MockRedisCacheService):
        async def eval(self, script, keys, args):
            return 0

    redis = OverLimitRedis()
    limiter = RedisRateLimiter(
        redis=redis,
        max_requests=100,
        window_seconds=60,
        fail_open=False,
    )
    result = await limiter.is_allowed("test_client")
    assert result is False
