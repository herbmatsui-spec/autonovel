import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TaskRecoveryWorker:
    """
    障害発生時のタスク自動リカバリワーカー。
    サーキットブレーカーがOPENになったプロバイダを監視し、
    復旧後にタスクを再開します。
    """

    def __init__(self, recovery_interval_seconds: int = 30) -> None:
        self.recovery_interval_seconds = recovery_interval_seconds
        self._running = False
        self._pending_tasks: Dict[str, Dict[str, Any]] = {}

    async def start(self) -> None:
        """リカバリ監視を開始"""
        self._running = True
        await self._monitor()

    async def stop(self) -> None:
        """リカバリ監視を停止"""
        self._running = False

    async def _monitor(self) -> None:
        """定期的なリカバリチェック"""
        while self._running:
            await asyncio.sleep(self.recovery_interval_seconds)
            await self._check_recovery()

    async def _check_recovery(self) -> None:
        """復旧可能なタスクを検査"""
        for task_id, task in list(self._pending_tasks.items()):
            if task["status"] == "failed" and task["retry_count"] < 3:
                task["retry_count"] += 1
                task["status"] = "pending"
                logger.info(f"Task {task_id} marked for retry")

    def add_task(self, task_id: str, provider: str) -> None:
        """リカバリ対象タスクを登録"""
        self._pending_tasks[task_id] = {
            "provider": provider,
            "status": "pending",
            "retry_count": 0,
            "created_at": datetime.utcnow(),
        }

    def get_pending_tasks(self) -> Dict[str, Dict[str, Any]]:
        """保留中のタスク一覧を取得"""
        return self._pending_tasks.copy()
