"""Redis-backed sliding window rate limiter."""

import time

from src.services.redis_cache import RedisCacheService


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

        # Use Redis sorted set with timestamps as scores
        # Remove old entries outside the window
        await self.redis.zremrangebyscore(key, 0, window_start)

        # Count current requests in window
        current_count = await self.redis.zcard(key)

        if current_count >= self.max_requests:
            return False

        # Add current request
        await self.redis.zadd(key, {str(now): now})
        # Set expiry on the key to clean up abandoned clients
        await self.redis.expire(key, self.window_seconds + 1)
        return True
