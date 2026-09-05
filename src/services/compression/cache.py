"""Intermediate Representation Cache for Context Compression (Step 32)."""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CompressionCache:
    """Redis-backed or in-memory cache for compressed context representations."""

    def __init__(self, redis_client: Any = None, default_ttl: int = 3600) -> None:
        self.redis_client = redis_client
        self.default_ttl = default_ttl
        self._memory_cache: dict[str, tuple[float, dict[str, Any]]] = {}

    def make_key(
        self,
        book_id: int | None,
        ep_num: int | None,
        scene_type: str,
        content_hash: str,
    ) -> str:
        """Generate consistent cache key."""
        raw = f"ctx_comp:{book_id or 0}:{ep_num or 0}:{scene_type}:{content_hash}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> dict[str, Any] | None:
        """Get cached compressed representation."""
        # 1. Redis 読み込み試行
        if self.redis_client:
            try:
                data = self.redis_client.get(key)
                if data:
                    if isinstance(data, bytes):
                        data = data.decode("utf-8")
                    return json.loads(data)
            except Exception as e:
                logger.debug(f"Redis get failed: {e}")

        # 2. インメモリフォールバック
        if key in self._memory_cache:
            exp, val = self._memory_cache[key]
            if time.time() < exp:
                return val
            else:
                del self._memory_cache[key]

        return None

    def set(self, key: str, value: dict[str, Any], ttl: int | None = None) -> None:
        """Store compressed representation in cache."""
        exp_sec = ttl or self.default_ttl

        # 1. Redis 保存試行
        if self.redis_client:
            try:
                serialized = json.dumps(value, ensure_ascii=False)
                self.redis_client.setex(key, exp_sec, serialized)
                return
            except Exception as e:
                logger.debug(f"Redis set failed: {e}")

        # 2. インメモリ保存
        self._memory_cache[key] = (time.time() + exp_sec, value)
        # 容量制限（最大1000件）
        if len(self._memory_cache) > 1000:
            oldest_key = min(self._memory_cache.keys(), key=lambda k: self._memory_cache[k][0])
            self._memory_cache.pop(oldest_key, None)


__all__ = ["CompressionCache"]
