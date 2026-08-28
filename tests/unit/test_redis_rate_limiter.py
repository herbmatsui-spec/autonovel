import pytest
from unittest.mock import AsyncMock

from src.backend.rate_limit import RedisRateLimiter, _RATE_LIMIT_LUA_SCRIPT

@pytest.mark.asyncio
async def test_rate_limiter_script_contains_required_commands():
    # Ensure the Lua script includes the expected atomic operations
    assert "ZREMRANGEBYSCORE" in _RATE_LIMIT_LUA_SCRIPT
    assert "ZCARD" in _RATE_LIMIT_LUA_SCRIPT
    assert "ZADD" in _RATE_LIMIT_LUA_SCRIPT

@pytest.mark.asyncio
async def test_rate_limiter_allows_and_limits(monkeypatch):
    # Mock RedisCacheService with eval returning sequential results
    mock_redis = AsyncMock()
    mock_redis.eval.side_effect = [1, 1, 0]  # two allowed, then rate‑limited
    limiter = RedisRateLimiter(redis=mock_redis, max_requests=2, window_seconds=60)

    # First two calls should be allowed
    assert await limiter.is_allowed("client1") is True
    assert await limiter.is_allowed("client1") is True
    # Third call should be denied
    assert await limiter.is_allowed("client1") is False
    # Verify eval was called three times with the correct script and key list
    assert mock_redis.eval.call_count == 3
    for call in mock_redis.eval.call_args_list:
        args, _ = call
        script, keys, args_list = args
        assert script == _RATE_LIMIT_LUA_SCRIPT
        # keys should contain the rate‑limit key for the client
        assert isinstance(keys, list) and len(keys) == 1
        assert isinstance(args_list, list) and len(args_list) == 4

@pytest.mark.asyncio
async def test_rate_limiter_fail_open_on_none(monkeypatch):
    mock_redis = AsyncMock()
    mock_redis.eval.return_value = None  # Simulate Redis error returning None
    limiter = RedisRateLimiter(redis=mock_redis, max_requests=5, window_seconds=60)
    # Should treat None as allowed (fail‑open)
    assert await limiter.is_allowed("client2") is True

@pytest.mark.asyncio
async def test_rate_limiter_fail_open_on_exception(monkeypatch):
    mock_redis = AsyncMock()
    mock_redis.eval.side_effect = Exception("Redis failure")
    limiter = RedisRateLimiter(redis=mock_redis, max_requests=5, window_seconds=60)
    # Exception should be caught and treated as allowed (fail‑open)
    assert await limiter.is_allowed("client3") is True
