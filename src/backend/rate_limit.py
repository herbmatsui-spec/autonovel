"""Redis-backed sliding window rate limiter."""

import logging
import time

from src.services.redis_cache import RedisCacheService
from src.backend.error_utils import log_exception

try:
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover
    class RedisError(Exception):
        """Fallback when redis package is unavailable."""

logger = logging.getLogger(__name__)

RATE_LIMIT_FAIL_OPEN: bool = False

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


class RedisRateLimiter:
    """Redis-backed sliding window rate limiter.

    Uses a sorted set per client to track request timestamps.
    デフォルトではフェイルクローズ（Redis障害時はリクエストを拒否）。
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
        Redis障害時はfail_open設定に従う（デフォルトはFalse:拒否）。
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
                    f" Failing {'open' if self.fail_open else 'close'}."
                )
                return self.fail_open
            return bool(result)
        except (RedisError, OSError) as e:
            log_exception(logger, "Rate limit check failed", e)
            if self.fail_open:
                return True
            return False
