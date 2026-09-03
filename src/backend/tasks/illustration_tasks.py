"""挿絵バッチ Huey タスク。

Issue #6: バッチエンドポイントを非同期化し、進捗を
``/api/illustrations/status/{task_id}`` で取得できるようにする。
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

from src.backend import database
from src.backend.database.repository import BookRepository
from src.backend.tasks.huey import huey

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _update_task(task_id: str, status: str, result_json: str | None = None) -> None:
    session = database.SessionLocal()
    try:
        repo = BookRepository(session)
        if result_json is not None:
            repo.set_task_result(task_id, result_json)
        else:
            repo.update_task_status(task_id, status)
    except Exception:
        session.rollback()
        logger.exception("Illustration task DB update failed: %s", task_id)
    finally:
        session.close()


async def _run_illustration_batch(book_id: int, settings: dict) -> dict[str, Any]:
    """AppContainer 経由で IllustrationWorkflow を呼んでバッチ実行。"""
    from src.dependencies import get_illustration_workflow

    workflow = get_illustration_workflow()

    class _ReporterShim:
        def __init__(self, id: str):
            self.id = id

        def report(self, message: str, level: str = "info") -> None:
            pass

        def update_progress(
            self, current: int, total: int, message: str = "", sub_message: str = ""
        ) -> None:
            pass

        @property
        def state(self):
            class _S:
                def should_stop(self) -> bool:
                    return False

            return _S()

    reporter = _ReporterShim(id=f"batch_{book_id}")
    return await workflow.execute(reporter=reporter, book_id=book_id, settings=settings)


@huey.task()
def illustrate_batch_task(book_id: int, settings: dict) -> dict[str, Any]:
    """非同期で挿絵バッチを実行する Huey タスク。"""
    task_id = f"illust_{uuid.uuid4().hex[:8]}"
    logger.info("Illustration batch task started: book_id=%s task_id=%s", book_id, task_id)
    _update_task(task_id, "processing")
    try:
        result = _run_async(_run_illustration_batch(book_id, settings))
        _update_task(task_id, "completed", result_json=json.dumps(result, default=str))
        return result
    except Exception as e:  # noqa: BLE001
        logger.exception("Illustration batch task failed: %s", task_id)
        _update_task(task_id, "failed")
        return {"status": "error", "message": str(e)}


__all__ = ["illustrate_batch_task"]
