# src/shared/redis_pool.py
"""Redis 接続プール管理（シングルトン）。"""

from __future__ import annotations

import os
from typing import Optional

import redis.asyncio as redis


_redis_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None


def get_redis_pool() -> redis.ConnectionPool:
    """Redis 接続プールを取得（シングルトン）。"""
    global _redis_pool
    if _redis_pool is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        max_connections = int(os.environ.get("REDIS_MAX_CONNECTIONS", "50"))
        _redis_pool = redis.ConnectionPool.from_url(
            redis_url,
            max_connections=max_connections,
            decode_responses=True,
        )
    return _redis_pool


def get_redis_client() -> redis.Redis:
    """Redis クライアントを取得（シングルトン）。"""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(connection_pool=get_redis_pool())
    return _redis_client


async def close_redis_pool() -> None:
    """接続プールをクローズ（アプリ終了時）。"""
    global _redis_pool, _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
