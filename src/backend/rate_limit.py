"""最小限の IP ベースレートリミッター (プロセス内)."""
from __future__ import annotations

import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request


class RateLimiter:
    """スライディングウィンドウ方式の軽量レートリミッター."""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._lock = threading.Lock()
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        with self._lock:
            timestamps = self._requests[client_ip]
            # ウィンドウ外のタイムスタンプを除去
            self._requests[client_ip] = [
                t for t in timestamps if now - t < self._window
            ]
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


generate_limiter = RateLimiter(max_requests=10, window_seconds=60)

__all__ = ["RateLimiter", "generate_limiter"]
