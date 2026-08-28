"""Redis-backed sliding window rate limiter."""

import time
import logging
from typing import Optional

from src.services.redis_cache import RedisCacheService

logger = logging.getLogger(__name__)

# Lua script for atomic sliding window rate limit
_RATE_LIMIT_LUA_SCRIPT = """
local key = KEYS[1]
local window_start = tonumber(ARGV[1])
local now = tonumber(ARGV[2])
local max_requests = tonumber(ARGV[3])
local window_seconds = tonumber(ARGV[4])

redis.call('ZREMRANGEBYSCORE', key, 0, window_start)
local current_count = redis.call('ZCARD', key)
if current_count < max_requests then
    redis.call('ZADD', key, now, now)
    redis.call('EXPIRE', key, window_seconds + 1)
    return 1
else
    return 0
end
"""


class RedisRateLimiter:
    """Redis-backed sliding window rate limiter.

    Uses a sorted set per client to track request timestamps.
    """

    def __init__(
        self,
        redis: RedisCacheService,
        max_requests: int,
        window_seconds: int,
    ):
        self.redis = redis
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def _get_key(self, client_id: str) -> str:
        return f"rate_limit:{client_id}"

    async def is_allowed(self, client_id: str) -> bool:
        """Check if request is allowed under rate limit.

        Returns True if allowed, False if rate limited.
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
            # If the script returns 1, allowed; 0, not allowed.
            # If eval returns None (Redis error), we fail open (allow) to maintain availability.
            if result is None:
                logger.warning(
                    "Rate limit Lua script evaluation failed (Redis unavailable). Failing open."
                )
                return True
            return bool(result)
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}", exc_info=True)
            # Fail open on unexpected errors
            return True