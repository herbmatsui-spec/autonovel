import logging
import os

import redis
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis_client = None
_redis_available = None
_async_redis_client = None
_async_redis_available = None


def get_redis_client():
    global _redis_client, _redis_available
    if _redis_available is False:
        return None
    if _redis_client is not None:
        return _redis_client

    try:
        # Try pinging Redis with a short timeout to check availability
        client = redis.from_url(REDIS_URL, socket_timeout=1.0, socket_connect_timeout=1.0)
        # Use ping() instead of hello() for broader compatibility (e.g. Windows Redis/Memurai)
        client.ping()
        _redis_client = client
        _redis_available = True
        logger.info("Successfully connected to Redis.")
        return _redis_client
    except Exception as e:
        _redis_available = False
        logger.warning(f"Redis is not available: {e}. Falling back to SQLite.")
        return None


async def get_async_redis_client():
    """非同期Redisクライアントを取得（接続失敗時はNoneを返す）."""
    global _async_redis_client, _async_redis_available
    if _async_redis_available is False:
        return None
    if _async_redis_client is not None:
        return _async_redis_client

    try:
        # Try pinging Redis with a short timeout to check availability
        client = aioredis.from_url(REDIS_URL, socket_timeout=1.0, socket_connect_timeout=1.0)
        await client.ping()
        _async_redis_client = client
        _async_redis_available = True
        logger.info("Successfully connected to async Redis.")
        return _async_redis_client
    except Exception as e:
        _async_redis_available = False
        logger.warning(f"Async Redis is not available: {e}. Falling back to SQLite.")
        return None


def is_redis_available():
    return get_redis_client() is not None


async def is_async_redis_available():
    return await get_async_redis_client() is not None
