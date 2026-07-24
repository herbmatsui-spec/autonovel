"""
streamlit_app/utils/async_manager.py — 非同期タスクの統合管理
"""
import asyncio
import logging
from typing import Any, Coroutine, Dict, TypeVar

from streamlit_app.utils.async_helper import run_async

logger = logging.getLogger(__name__)

T = TypeVar("T")

class AsyncTaskManager:
    """
    アプリケーション全体で非同期タスクのライフサイクルを管理する。
    並列リクエストの制御や、キャンセル可能なタスクの管理を行う。
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AsyncTaskManager, cls).__new__(cls)
            cls._instance._tasks: Dict[str, asyncio.Task] = {}
        return cls._instance

    def run_parallel(self, coros: list[Coroutine[Any, Any, T]]) -> list[T]:
        """
        複数のコルーチンを並列に実行し、すべての結果が揃うまで待機する。
        """
        async def _gather():
            return await asyncio.gather(*coros, return_exceptions=True)

        results = run_async(_gather())

        # 例外が発生している場合はログに記録
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"Parallel task {i} failed: {res}")

        return results

    def spawn_task(self, task_id: str, coro: Coroutine[Any, Any, T]) -> asyncio.Task:
        """
        タスクをバックグラウンドで開始し、管理下に置く。
        """
        loop = asyncio.get_event_loop()
        task = loop.create_task(coro)
        self._tasks[task_id] = task

        def _cleanup(_):
            self._tasks.pop(task_id, None)

        task.add_done_callback(_cleanup)
        return task

    def cancel_task(self, task_id: str):
        """特定のタスクをキャンセルする"""
        task = self._tasks.get(task_id)
        if task:
            task.cancel()
            logger.info(f"Task {task_id} cancelled.")

    def cancel_all(self):
        """すべての管理タスクをキャンセルする"""
        for task_id in list(self._tasks.keys()):
            self.cancel_task(task_id)

async_task_manager = AsyncTaskManager()
