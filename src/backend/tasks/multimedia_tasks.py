"""src/backend/tasks/multimedia_tasks.py - Huey tasks for Audio & Multimedia generation (Step 18)."""
from __future__ import annotations

import logging
from typing import Any

from src.backend.tasks.huey import huey

logger = logging.getLogger(__name__)


@huey.task(retries=2, retry_delay=10)
def generate_asset_pack_task(
    book_id: int,
    task_id: str | None = None,
    include_if_routes: bool = True,
    include_media_mix: bool = True,
    include_ebook: bool = True,
    include_audio: bool = True,
    ebook_formats: list[str] = ["epub", "pdf"],
    media_mix_formats: list[str] = ["manga"],
) -> dict[str, Any]:
    """Asset Pack 生成 Huey タスク。"""
    from src.backend.multimedia_service import MultimediaService

    service = MultimediaService()
    try:
        result, task_id = service.generate_asset_pack(
            book_id=book_id,
            include_if_routes=include_if_routes,
            include_media_mix=include_media_mix,
            include_ebook=include_ebook,
            include_audio=include_audio,
            ebook_formats=ebook_formats,
            media_mix_formats=media_mix_formats,
        )

        return {
            "task_id": task_id,
            "asset_id": result.asset_id,
            "files": result.files,
            "metadata": result.metadata,
            "file_count": len(result.files)
        }
    except Exception as exc:
        logger.warning(f"generate_asset_pack_task failed for book {book_id}: {exc}")
        return {
            "task_id": task_id,
            "error": str(exc),
            "file_count": 0,
        }
