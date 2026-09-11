"""最小限の IP ベースレートリミッター (Redis分散対応 + プロセス内フォールバック)."""

from __future__ import annotations

import logging
import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request

from src.backend.redis_util import get_redis_client

logger = logging.getLogger(__name__)


class RateLimiter:
    """スライディングウィンドウ方式のレートリミッター (Redis対応・メモリフォールバック)."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60, prefix: str = "rate_limit") -> None:
        self._max = max_requests
        self._window = window_seconds
        self._prefix = prefix
        self._lock = threading.Lock()
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def check(self, request: Request) -> None:
        client_ip = self._get_client_ip(request)

        # 1. Redis が利用可能な場合は Redis カウンタで分散チェック
        redis_client = get_redis_client()
        if redis_client is not None:
            try:
                key = f"{self._prefix}:{client_ip}"
                current_count = redis_client.incr(key)
                if current_count == 1:
                    redis_client.expire(key, self._window)
                if current_count > self._max:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded. Try again later.",
                    )
                return
            except HTTPException:
                raise
            except Exception as e:
                logger.debug("Redis rate limiter check failed, falling back to memory: %s", e)

        # 2. メモリ内フォールバック
        now = time.time()
        with self._lock:
            timestamps = self._requests[client_ip]
            self._requests[client_ip] = [t for t in timestamps if now - t < self._window]
            if len(self._requests[client_ip]) >= self._max:
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded. Try again later.",
                )
            self._requests[client_ip].append(now)

    def reset(self) -> None:
        """テスト用のリセットメソッド."""
        with self._lock:
            self._requests.clear()


generate_limiter = RateLimiter(max_requests=10, window_seconds=60, prefix="rate_limit:gen")
stream_limiter = RateLimiter(max_requests=3, window_seconds=60, prefix="rate_limit:stream")

__all__ = ["RateLimiter", "generate_limiter", "stream_limiter"]

