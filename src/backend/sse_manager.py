"""
src/backend/sse_manager.py - Server-Sent Events (SSE) 接続・イベント管理マネージャー
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, Optional, Set

logger = logging.getLogger(__name__)


class SSEManager:
    """SSE接続クライアントを管理し、イベントを非同期ブロードキャストするマネージャー"""

    _instance: Optional["SSEManager"] = None

    def __new__(cls, *args, **kwargs) -> "SSEManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._queues: Set[asyncio.Queue[str]] = set()
        self._lock: Optional[asyncio.Lock] = None
        self._initialized = True
        logger.info("[SSEManager] Initialized SSEManager singleton.")

    @property
    def lock(self) -> asyncio.Lock:
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    async def register(self) -> asyncio.Queue[str]:
        """新規クライアント用のイベントキューを登録する"""
        queue: asyncio.Queue[str] = asyncio.Queue(maxsize=100)
        async with self.lock:
            self._queues.add(queue)
        logger.info(f"[SSEManager] Client connected. Total active clients: {len(self._queues)}")
        return queue

    async def unregister(self, queue: asyncio.Queue[str]) -> None:
        """切断されたクライアントのイベントキューを削除する"""
        async with self.lock:
            self._queues.discard(queue)
        logger.info(f"[SSEManager] Client disconnected. Remaining clients: {len(self._queues)}")

    async def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        """接続中のすべてのクライアントへイベントをブロードキャストする"""
        payload = {
            "event": event_type,
            "timestamp": time.time(),
            "data": data,
        }
        message = f"event: {event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"

        async with self.lock:
            dead_queues = set()
            for queue in self._queues:
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    logger.warning("[SSEManager] Client queue is full, dropping message.")
                except Exception as e:
                    logger.error(f"[SSEManager] Failed to put message into queue: {e}")
                    dead_queues.add(queue)
            for dead in dead_queues:
                self._queues.discard(dead)

    async def event_generator(self, queue: asyncio.Queue[str]) -> AsyncGenerator[str, None]:
        """クライアント接続中にイベントストリームを生成し、定期的にハートビートを送信する"""
        try:
            # 接続直後に接続確認イベントを送信
            initial_msg = {
                "event": "connected",
                "timestamp": time.time(),
                "data": {"status": "ok", "message": "SSE Stream Connected"},
            }
            yield f"event: connected\ndata: {json.dumps(initial_msg, ensure_ascii=False)}\n\n"

            while True:
                try:
                    # 15秒タイムアウトでキューからイベントを取得（タイムアウト時はPingを送信）
                    message = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield message
                except asyncio.TimeoutError:
                    # ハートビート
                    ping_msg = {
                        "event": "ping",
                        "timestamp": time.time(),
                        "data": {"type": "heartbeat"},
                    }
                    yield f"event: ping\ndata: {json.dumps(ping_msg, ensure_ascii=False)}\n\n"
        except asyncio.CancelledError:
            logger.info("[SSEManager] Stream generator cancelled by client disconnect.")
        finally:
            await self.unregister(queue)


# グローバルアクセス用ヘルパー
_global_sse_manager = SSEManager()


def get_sse_manager() -> SSEManager:
    """SSEManager シングルトンインスタンスを取得する"""
    return _global_sse_manager
