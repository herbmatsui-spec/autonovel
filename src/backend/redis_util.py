import logging
import os

import redis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

_redis_client = None
_redis_available = None

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

def is_redis_available():
    return get_redis_client() is not None

