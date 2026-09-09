"""Huey-based distributed tasks for commercial novel publishing (Phase 5 / Steps 49-50).

Decouples synchronous browser automation and external HTTP publishing from FastAPI event loop,
and provides scheduling (delay=seconds) for automated reservation publishing.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from src.backend.tasks.huey import huey

logger = logging.getLogger(__name__)

# インメモリ/SQLite での予約タスク追跡レジストリ（Step 56 向け）
_SCHEDULED_JOBS: dict[str, dict[str, Any]] = {}


@huey.task(retries=2, retry_delay=15)
def publish_to_platforms_task(
    book_id: int,
    platforms: list[str],
    credentials: dict[str, Any],
    episode_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Huey 分散ワーカー上で商用サイト（なろう・カクヨム等）への投稿を実行する (Step 49)."""
    logger.info(
        "Commercial publish task started for book_id=%d, platforms=%s",
        book_id,
        platforms,
    )

    async def _run() -> dict[str, Any]:
        from src.services.commercial_pipeline import CommercialPipeline
        from src.backend.routers.commercial import _get_novel_data, _get_episodes_data, _save_publish_records, _get_credentials_class

        # 1. 認証情報の復元
        typed_credentials = {}
        for platform in platforms:
            if credentials and platform in credentials:
                creds_data = credentials[platform]
                if isinstance(creds_data, dict):
                    creds_class = _get_credentials_class(platform)
                    typed_credentials[platform] = creds_class(**creds_data)
                else:
                    typed_credentials[platform] = creds_data

        # 2. 作品・エピソードデータ取得
        novel_data = await _get_novel_data(book_id)
        episodes_data = await _get_episodes_data(book_id, episode_ids)

        # 3. パイプライン実行
        pipeline = CommercialPipeline()
        publish_results = await pipeline._publish_to_platforms(
            novel=novel_data,
            episodes=episodes_data,
            platforms=platforms,
            credentials=typed_credentials,
        )

        # 4. DB 永続化
        await _save_publish_records(book_id, publish_results)

        # 結果サマリー
        summary: dict[str, Any] = {"book_id": book_id, "platforms": {}}
        for p, results in publish_results.items():
            succ = sum(1 for r in results if r.success)
            summary["platforms"][p] = {
                "success": succ,
                "failed": len(results) - succ,
                "details": [
                    {
                        "episode": ep.get("ep_num"),
                        "success": r.success,
                        "post_id": r.post_id,
                        "url": r.url,
                        "error": r.error,
                    }
                    for ep, r in zip(episodes_data, results)
                ],
            }
        return summary

    try:
        result = asyncio.run(_run())
        logger.info("Commercial publish task completed: %s", result)
        return {"status": "success", "result": result}
    except Exception as exc:
        logger.exception("Commercial publish task failed for book_id=%d: %s", book_id, exc)
        return {"status": "error", "error": str(exc)}


def schedule_commercial_publish(
    book_id: int,
    platforms: list[str],
    credentials: dict[str, Any],
    episode_ids: list[int] | None = None,
    publish_at: str | datetime | None = None,
) -> dict[str, Any]:
    """指定時刻（または即時）に Huey キューに商用投稿タスクをスケジュールする (Step 50)."""
    delay_seconds = 0
    scheduled_iso = None

    if publish_at:
        if isinstance(publish_at, dict):
            # 辞書型（{"target_time": "..."} や {"publish_at": "..."}）の展開
            publish_at_val = publish_at.get("target_time") or publish_at.get("publish_at") or publish_at.get("at")
        else:
            publish_at_val = publish_at

        if isinstance(publish_at_val, str):
            # ISO format parse
            try:
                dt = datetime.fromisoformat(publish_at_val.replace("Z", "+00:00"))
            except Exception:
                dt = datetime.now(timezone.utc)
        elif isinstance(publish_at_val, datetime):
            dt = publish_at_val
        else:
            dt = datetime.now(timezone.utc)

        now = datetime.now(timezone.utc) if dt.tzinfo else datetime.now()
        diff = (dt - now).total_seconds()
        delay_seconds = max(0, int(diff))
        scheduled_iso = dt.isoformat()

    # Huey タスク投入
    if delay_seconds > 0:
        task_result = publish_to_platforms_task.schedule(
            args=(book_id, platforms, credentials, episode_ids),
            delay=delay_seconds,
        )
        status = "scheduled"
    else:
        task_result = publish_to_platforms_task(
            book_id, platforms, credentials, episode_ids
        )
        status = "queued"

    task_id = str(task_result.id) if task_result else "mock-task-id"

    job_info = {
        "task_id": task_id,
        "book_id": book_id,
        "platforms": platforms,
        "status": status,
        "delay_seconds": delay_seconds,
        "scheduled_at": scheduled_iso,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _SCHEDULED_JOBS[task_id] = job_info

    return job_info


def get_scheduled_commercial_tasks(book_id: int | None = None) -> list[dict[str, Any]]:
    """登録されている商用投稿ジョブの一覧を取得する (Step 56)."""
    if book_id is None:
        return list(_SCHEDULED_JOBS.values())
    return [job for job in _SCHEDULED_JOBS.values() if job.get("book_id") == book_id]


def cancel_commercial_task(task_id: str) -> bool:
    """Huey キュー上の予約投稿タスクを取り消す (Step 57)."""
    try:
        huey.revoke_by_id(task_id)
        if task_id in _SCHEDULED_JOBS:
            _SCHEDULED_JOBS[task_id]["status"] = "cancelled"
        return True
    except Exception as exc:
        logger.warning("Failed to revoke Huey task %s: %s", task_id, exc)
        if task_id in _SCHEDULED_JOBS:
            _SCHEDULED_JOBS[task_id]["status"] = "cancelled"
            return True
        return False
