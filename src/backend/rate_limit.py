"""Redis-backed sliding window rate limiter."""

import logging
import time
import os
import asyncio
from typing import Dict, Tuple

from src.services.redis_cache import RedisCacheService
from src.backend.error_utils import log_exception

try:
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover
    class RedisError(Exception):
        """Fallback when redis package is unavailable."""

logger = logging.getLogger(__name__)

RATE_LIMIT_FAIL_OPEN: bool = os.getenv("RATE_LIMIT_FAIL_OPEN", "false").lower() in ("true", "1", "yes")

# Lua script for atomic sliding window rate limiting
# Removes expired entries, counts current requests, adds new request if under limit
_RATE_LIMIT_LUA_SCRIPT = """
local key = KEYS[1]
local window_start = tonumber(ARGV[1])
local now = tonumber(ARGV[2])
local max_requests = tonumber(ARGV[3])
local window_seconds = tonumber(ARGV[4])

-- Remove expired entries
redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

-- Count current requests in window
local count = redis.call('ZCARD', key)

if count < max_requests then
    -- Add new request with current timestamp as score
    redis.call('ZADD', key, now, now .. '-' .. math.random(1000000))
    return 1
else
    return 0
end
"""

# Token bucket fallback for when Redis is unavailable
_TOKEN_BUCKETS: Dict[str, Tuple[float, float]] = {}  # client_id -> (tokens, last_refill)
_TOKEN_BUCKET_LOCK = asyncio.Lock()


async def _token_bucket_allow(client_id: str, max_requests: int, window_seconds: int) -> bool:
    """Token bucket rate limiting fallback (in-memory, per-process).
    Returns True if allowed, False if rate limited.
    """
    rate = max_requests / window_seconds  # tokens per second
    now = time.time()
    async with _TOKEN_BUCKET_LOCK:
        tokens, last_refill = _TOKEN_BUCKETS.get(client_id, (float(max_requests), now))
        # Refill tokens based on elapsed time
        elapsed = now - last_refill
        tokens = min(float(max_requests), tokens + elapsed * rate)
        if tokens >= 1.0:
            tokens -= 1.0
            _TOKEN_BUCKETS[client_id] = (tokens, now)
            return True
        else:
            _TOKEN_BUCKETS[client_id] = (tokens, last_refill)
            return False


class RedisRateLimiter:
    """Redis-backed sliding window rate limiter with token bucket fallback.

    Uses a sorted set per client to track request timestamps.
    When Redis is unavailable, falls back to an in-memory token bucket per client.
    """

    def __init__(
        self,
        redis: RedisCacheService,
        max_requests: int,
        window_seconds: int,
        fail_open: bool = RATE_LIMIT_FAIL_OPEN,
    ):
        self.redis = redis
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.fail_open = fail_open

    def _get_key(self, client_id: str) -> str:
        return f"rate_limit:{client_id}"

    async def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed under rate limit.

        Returns True if allowed, False if rate limited.
        Redis障害時はローカル token bucket フォールバックを使用。
        """
        key = self._get_key(client_id)
        now = time.time()
        window_start = now - self.window_seconds

        try:
            result = await self.redis.eval(
                _RATE_LIMIT_LUA_SCRIPT,
                [key],
                [str(window_start), str(now), str(self.max_requests), str(self.window_seconds)],
            )
            if result is None:
                logger.warning(
                    "Rate limit Lua script evaluation failed (Redis unavailable)."
                    " Falling back to token bucket."
                )
                return await _token_bucket_allow(client_id, self.max_requests, self.window_seconds)
            return bool(result)
        except (RedisError, OSError) as e:
            log_exception(logger, "Rate limit check failed", e)
            logger.warning("Falling back to token bucket due to Redis error.")
            return await _token_bucket_allow(client_id, self.max_requests, self.window_seconds)
