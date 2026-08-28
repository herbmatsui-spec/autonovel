"""
src/backend/hitl_manager.py - Human-in-the-Loop (HITL) ワークフロー待機・介入マネージャー
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

from src.backend.sse_manager import get_sse_manager
from src.shared.domain_event_bus import DomainEvent, get_domain_event_bus

logger = logging.getLogger(__name__)


class HITLManager:
    """エージェント生成パイプラインの一時停止・人間のフィードバック介入・再開を統括するマネージャー"""

    _instance: Optional["HITLManager"] = None

    def __new__(cls, *args, **kwargs) -> "HITLManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._waiters: Dict[str, asyncio.Future] = {}
        self._pending_payloads: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
        self._initialized = True
        logger.info("[HITLManager] Initialized HITLManager singleton.")

    async def suspend(
        self,
        session_id: str,
        payload: Dict[str, Any],
        timeout: float = 300.0,
    ) -> Dict[str, Any]:
        """ワークフローを指定のsession_idで一時停止し、SSEで通知。再開またはタイムアウトまで待機する"""
        logger.info(f"[HITLManager] Suspending execution for session_id='{session_id}' (timeout={timeout}s)")
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()

        async with self._lock:
            self._waiters[session_id] = future
            self._pending_payloads[session_id] = {
                "session_id": session_id,
                "payload": payload,
                "created_at": time.time(),
                "timeout": timeout,
            }

        # SSE Manager へブロードキャスト通知
        sse_manager = get_sse_manager()
        await sse_manager.broadcast(
            "HITL_REQUIRED",
            {
                "session_id": session_id,
                "timeout_seconds": timeout,
                "payload": payload,
            },
        )

        # ドメインイベントバスへ発行
        event_bus = get_domain_event_bus()
        await event_bus.publish(
            "HITL_SUSPENDED",
            DomainEvent(
                type="HITL_SUSPENDED",
                payload={"session_id": session_id, "data": payload},
            ),
        )

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            logger.info(f"[HITLManager] Session '{session_id}' resumed by user input: {result}")
            return result
        except asyncio.TimeoutError:
            logger.warning(
                f"[HITLManager] Session '{session_id}' timed out after {timeout}s. Auto-resuming with defaults."
            )
            return {
                "session_id": session_id,
                "approved": True,
                "feedback": "Auto-resumed due to timeout.",
                "overrides": {},
                "status": "auto_resumed_timeout",
            }
        finally:
            async with self._lock:
                self._waiters.pop(session_id, None)
                self._pending_payloads.pop(session_id, None)

    async def resume(self, session_id: str, response_data: Dict[str, Any]) -> bool:
        """待機中のセッションにユーザーのフィードバックを与えてワークフローを再開する"""
        async with self._lock:
            future = self._waiters.get(session_id)
            if future is None or future.done():
                logger.warning(f"[HITLManager] No active waiter found for session_id='{session_id}'")
                return False

            future.set_result(response_data)

        # イベントバスへ発行
        event_bus = get_domain_event_bus()
        await event_bus.publish(
            "HITL_RESUMED",
            DomainEvent(
                type="HITL_RESUMED",
                payload={"session_id": session_id, "response": response_data},
            ),
        )

        # SSE Manager へ再開通知
        sse_manager = get_sse_manager()
        await sse_manager.broadcast(
            "HITL_RESUMED",
            {
                "session_id": session_id,
                "status": "resumed",
                "approved": response_data.get("approved", True),
            },
        )

        logger.info(f"[HITLManager] Successfully resumed session_id='{session_id}'")
        return True

    def get_pending(self) -> List[Dict[str, Any]]:
        """現在待機中のHITLセッション一覧を取得する"""
        return list(self._pending_payloads.values())


# シングルトン取得用ヘルパー
_global_hitl_manager = HITLManager()


def get_hitl_manager() -> HITLManager:
    """HITLManager シングルトンインスタンスを取得する"""
    return _global_hitl_manager
