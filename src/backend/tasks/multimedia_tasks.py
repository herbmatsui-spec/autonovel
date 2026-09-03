"""Multimedia 系の Huey タスク。

`generate_asset_pack` を非同期に実行し、DB のタスク状態を更新する。
"""

from __future__ import annotations

import logging

from src.backend.multimedia_service import MultimediaService
from src.backend.tasks.huey import huey

logger = logging.getLogger(__name__)


@huey.task()
def generate_asset_pack_task(
    task_id: str,
    book_id: int,
    include_if_routes: bool = True,
    include_media_mix: bool = True,
    include_ebook: bool = True,
    ebook_formats: list[str] | None = None,
    media_mix_formats: list[str] | None = None,
) -> dict[str, int | str | None]:
    """`MultimediaService.generate_asset_pack` を非同期実行する。"""
    service = MultimediaService()
    try:
        result, _ = service.generate_asset_pack(
            book_id=book_id,
            include_if_routes=include_if_routes,
            include_media_mix=include_media_mix,
            include_ebook=include_ebook,
            ebook_formats=ebook_formats or ["epub", "pdf"],
            media_mix_formats=media_mix_formats or ["manga"],
        )
        return {
            "asset_id": result.asset_id or 0,
            "file_count": len(result.files),
            "file_path": result.files[0] if result.files else None,
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("generate_asset_pack_task failed: %s", exc)
        with service._session() as s:  # type: ignore[attr-defined]
            service.update_task(s, task_id, status="failed", error=str(exc))
            s.commit()
        return {"asset_id": 0, "file_count": 0, "file_path": None, "error": str(exc)}
