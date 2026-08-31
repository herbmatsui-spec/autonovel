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
from src.backend.observability import metrics
from src.backend.tasks.huey import huey

logger = logging.getLogger(__name__)


def _run_async(coro: Any) -> Any:
    """新規 event loop を作成して coroutine を同期実行する。"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
        asyncio.set_event_loop(None)


async def _generate(payload: dict[str, Any]) -> dict[str, Any]:
    """タスク本体。``generate_with_llm`` 遅延 import で循環参照を回避する。"""
    from src.backend.routers.easy_mode import generate_with_llm

    return await generate_with_llm(payload)


def _persist_success(repo: BookRepository, task_id: int, result: dict[str, Any]) -> None:
    """成功時の DB 永続化処理。"""
    repo.set_task_result(task_id, json.dumps(result, ensure_ascii=False))


def _mark_failed(repo: BookRepository, task_id: int, exc: Exception) -> None:
    """失敗時のステータス更新。"""
    repo.update_task_status(task_id, "failed")
    logger.exception("Generation task failed (task_id=%s): %s", task_id, exc)


@huey.task()
def generate_chapter_task(payload: dict[str, Any]) -> dict[str, Any]:
    """
    非同期で小説の章を生成する Huey タスク。
    ワーカー上で ``generate_with_llm`` を実行し、結果を DB に保存する。
    """
    logger.info("Starting generation task: %s", payload)
    task_id = payload.get("task_id")

    try:
        result = _run_async(_generate(payload))
        if task_id:
            session = database.SessionLocal()
            try:
                repo = BookRepository(session)
                _persist_success(repo, int(task_id), result)
            finally:
                session.close()
        metrics.increment("tasks_completed")
        logger.info("Generation task completed: task_id=%s", task_id)
        return result
    except Exception as exc:
        logger.exception("Generation task failed: %s", exc)
        metrics.increment("tasks_failed")
        if task_id:
            session = database.SessionLocal()
            try:
                repo = BookRepository(session)
                _mark_failed(repo, int(task_id), exc)
            finally:
                session.close()
        return {"error": str(exc), "text": "", "time": 0}


__all__: list[str] = ["generate_chapter_task"]
