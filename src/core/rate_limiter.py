from __future__ import annotations

import asyncio
import time
from typing import Optional

from src.core.observability import StructuredLogger

logger = StructuredLogger(__name__)

class TokenBucket:
    """
    Token Bucketアルゴリズムに基づいたレートリミッター。
    APIリクエストの流量を制御し、429 Too Many Requestsを未然に防ぐ。
    """
    def __init__(
        self,
        capacity: float,
        fill_rate: float,
        name: str = "default"
    ):
        """
        Args:
            capacity: バケットの最大容量（最大バースト量）
            fill_rate: 1秒あたりのトークン補充量
            name: リミッターの識別名（ログ用）
        """
        self.capacity = capacity
        self.fill_rate = fill_rate
        self.name = name
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock: Optional[asyncio.Lock] = None

    def _get_lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def consume(self, tokens: float = 1.0) -> bool:
        """
        トークンを消費しようと試みる。
        
        Args:
            tokens: 消費するトークン数（通常は1リクエスト=1トークン）
            
        Returns:
            True: 消費に成功し、リクエストを即座に実行可能
            False: トークン不足によりリクエスト不可
        """
        async with self._get_lock():
            self._refill()
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

    def _refill(self):
        """現在の時刻に基づいてトークンを補充する。"""
        now = time.monotonic()
        delta = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + delta * self.fill_rate)
        self.last_update = now

    async def wait_and_consume(self, tokens: float = 1.0):
        """
        トークンが補充されるまで待機し、消費する。
        """
        while True:
            async with self._get_lock():
                self._refill()
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return

                # 次にトークンが補充されるまでの待機時間を計算
                wait_time = (tokens - self.tokens) / self.fill_rate

            logger.debug(f"RateLimiter [{self.name}]: Token shortage. Waiting {wait_time:.2f}s...")
            # ジッターを追加して、同時に待機していた大量のリクエストが一度に集中する「サンダリングヘルド」を防ぐ
            import random
            jitter = random.uniform(0, 0.1)
            await asyncio.sleep(wait_time + jitter)

    async def adjust_rate(self, factor: float):
        """
        補充レートを動的に調整する（AdaptiveCooldownからのフィードバック用）。
        
        Args:
            factor: 乗数 (例: 0.5 でレート半分に低下, 1.1 で10%回復)
        """
        async with self._get_lock():
            old_rate = self.fill_rate
            self.fill_rate = max(0.01, self.fill_rate * factor)
            logger.info(f"RateLimiter [{self.name}]: Adjusted fill_rate {old_rate:.2f} -> {self.fill_rate:.2f} (factor={factor})")

    def get_status(self) -> dict:
        """現在のバケット状態を返す。"""
        return {
            "name": self.name,
            "tokens": self.tokens,
            "capacity": self.capacity,
            "fill_rate": self.fill_rate
        }
