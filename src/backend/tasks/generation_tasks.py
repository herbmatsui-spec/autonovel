"""非同期章生成タスク。

Huey ワーカー上で実行される ``generate_chapter_task`` を提供する。
タスクは ``generate_with_llm`` を呼び出して生成結果を取得し、
DB 上の ``Task`` レコードへ結果を永続化する。
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from src.backend import database
from src.backend.database.repository import BookRepository
from src.backend.observability.health import metrics
from src.backend.tasks.huey import huey

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    """新規 event loop を作成して coroutine を同期実行する。"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _generate(payload: dict[str, Any]) -> dict[str, Any]:
    """タスク本体。``generate_with_llm`` 遅延 import で循環参照を回避する。"""
    from src.backend.routers.easy_mode import generate_with_llm

    return await generate_with_llm(payload)


def _update_task_in_db(
    task_id: str,
    status: str,
    result_json: str | None = None,
) -> None:
    """DB 上の Task レコードを安全に更新する (rollback 保証付き)。"""
    session = database.SessionLocal()
    try:
        repo = BookRepository(session)
        if status == "completed" and result_json is not None:
            repo.set_task_result(task_id, result_json)
        else:
            repo.update_task_status(task_id, status)
    except Exception:
        session.rollback()
        logger.exception("DB update failed for task_id=%s status=%s", task_id, status)
    finally:
        session.close()


@huey.task()
def generate_chapter_task(payload: dict[str, Any]) -> dict[str, Any]:
    """非同期で小説の章を生成する Huey タスク。

    ワーカー上で ``generate_with_llm`` を実行し、結果を DB に保存する。
    """
    logger.info("Starting generation task: %s", payload)
    task_id = payload.get("task_id")

    try:
        result = _run_async(_generate(payload))
        metrics.increment("tasks_completed")
        logger.info("Generation task completed: task_id=%s", task_id)
        if task_id:
            _update_task_in_db(
                str(task_id),
                "completed",
                json.dumps(result, ensure_ascii=False),
            )
        return result
    except Exception as exc:
        logger.exception("Generation task failed: %s", exc)
        metrics.increment("tasks_failed")
        if task_id:
            _update_task_in_db(str(task_id), "failed")
        return {"error": str(exc), "text": "", "time": 0}


__all__: list[str] = ["generate_chapter_task"]
