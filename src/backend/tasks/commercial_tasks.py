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
def execute_publication_task(schedule_id: int) -> dict[str, Any]:
    """
    予約投稿スケジュールに基づき、実際の投稿処理を実行する (Step 7, 8).
    DBステータスの遷移 (pending -> running -> completed/failed) を管理する。
    """
    logger.info("Execute publication task started for schedule_id=%d", schedule_id)

    async def _run() -> dict[str, Any]:
        from sqlalchemy import select
        from src.backend.database.models import PublicationScheduleModel
        from src.backend.database.uow import UnitOfWork
        from src.core.container import AppContainer
        from src.backend.services.commercial_helpers import _get_novel_data, _get_episodes_data
        from src.backend.routers.commercial import _save_publish_records, _get_credentials_class
        from src.services.commercial_pipeline import CommercialPipeline

        async with UnitOfWork(AppContainer.db()) as uow:
            if uow.session is None:
                raise RuntimeError("Database session not initialized")

            # 1. スケジュールの取得とステータス更新 (pending -> running)
            result = await uow.session.execute(
                select(PublicationScheduleModel).where(PublicationScheduleModel.id == schedule_id)
            )
            schedule = result.scalar_one_or_none()
            if not schedule:
                return {"status": "error", "error": f"Schedule {schedule_id} not found"}

            if schedule.status != "pending":
                return {"status": "error", "error": f"Schedule {schedule_id} is not pending (status: {schedule.status})"}

            schedule.status = "running"
            await uow.session.commit()
            await uow.session.refresh(schedule)

            try:
                # 2. 投稿データの準備
                book_id = schedule.book_id
                platform = schedule.platform
                
                # エピソード範囲からIDリストを抽出
                # 実際には Chapter モデルから ep_num の範囲で取得する
                from src.backend.database.models import Chapter
                ch_result = await uow.session.execute(
                    select(Chapter.id)
                    .where(Chapter.book_id == book_id)
                    .where(Chapter.ep_num >= schedule.episode_range_start)
                    .where(Chapter.ep_num <= schedule.episode_range_end)
                    .order_by(Chapter.ep_num)
                )
                episode_ids = [r[0] for r in ch_result.all()]

                # 認証情報の準備 (DBに保存されていない場合は環境変数等から取得される想定)
                # ここでは簡易的に空の辞書を渡し、pipeline側でデフォルトを処理させる
                credentials = {}
                
                # 3. 投稿実行
                novel_data = await _get_novel_data(book_id)
                episodes_data = await _get_episodes_data(book_id, episode_ids, platforms=[platform])
                
                pipeline = CommercialPipeline()
                publish_results = await pipeline._publish_to_platforms(
                    novel=novel_data,
                    episodes=episodes_data,
                    platforms=[platform],
                    credentials=credentials,
                )

                # 4. 投稿結果の保存
                await _save_publish_records(book_id, publish_results)

                # 5. ステータス更新 (running -> completed)
                # 全プラットフォームで成功したか判定
                all_success = True
                for p, results in publish_results.items():
                    if any(not r.success for r in results):
                        all_success = False
                        break
                
                if all_success:
                    schedule.status = "completed"
                    error_msg = None
                else:
                    schedule.status = "failed"
                    error_msg = "Some episodes failed to publish"

                if error_msg:
                    schedule.error_message = error_msg

                await uow.session.commit()
                return {"status": "success", "schedule_id": schedule_id, "final_status": schedule.status}

            except Exception as e:
                logger.exception("Publication execution failed for schedule_id=%d: %s", schedule_id, e)
                schedule.status = "failed"
                schedule.error_message = str(e)
                await uow.session.commit()
                return {"status": "error", "error": str(e)}

    try:
        result = asyncio.run(_run())
        logger.info("Execute publication task completed: %s", result)
        return result
    except Exception as exc:
        logger.exception("Execute publication task wrapper failed for schedule_id=%d: %s", schedule_id, exc)
        return {"status": "error", "error": str(exc)}

@huey.task(retries=2, retry_delay=15)
def publish_to_platforms_task(
    book_id: int,
    platforms: list[str],
    credentials: dict[str, Any],
    episode_ids: list[int] | None = None,
) -> dict[str, Any]:
    """Huey 分散ワーカー上で商用サイト（なろう・カクヨム等）への投稿を実行する (Legacy/Direct)."""
    logger.info(
        "Commercial publish task started for book_id=%d, platforms=%s",
        book_id,
        platforms,
    )

    async def _run() -> dict[str, Any]:
        from src.services.commercial_pipeline import CommercialPipeline
        from src.backend.services.commercial_helpers import _get_novel_data, _get_episodes_data
        from src.backend.routers.commercial import _save_publish_records, _get_credentials_class

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
