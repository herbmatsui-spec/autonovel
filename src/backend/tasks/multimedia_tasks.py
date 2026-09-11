"""src/backend/tasks/multimedia_tasks.py - Huey tasks for Audio & Multimedia generation (Step 18)."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.backend.tasks.huey import huey

logger = logging.getLogger(__name__)


@huey.task(retries=2, retry_delay=10)
def synthesize_chapter_audio_task(
    book_id: int,
    episode_num: int,
    chapter_text: str,
    characters: list[str] | None = None,
) -> dict[str, Any]:
    """1話分の音声合成をバックグラウンド実行し、DBに永続化するタスク。"""
    logger.info("synthesize_chapter_audio_task started for book_id=%d, episode_num=%d", book_id, episode_num)

    async def _run() -> dict[str, Any]:
        from src.services.audio.chapter_synthesizer import ChapterAudioSynthesizer
        from src.backend.database.core import get_db_manager
        from src.backend.database.models import AudioAssetModel

        synth = ChapterAudioSynthesizer()
        result = await synth.synthesize_chapter(
            book_id=book_id,
            episode_num=episode_num,
            chapter_text=chapter_text,
            characters=characters,
        )

        file_path = result.get("file_path")
        if file_path:
            db_mgr = get_db_manager()
            async with db_mgr.session() as session:
                audio_asset = AudioAssetModel(
                    book_id=book_id,
                    episode_num=episode_num,
                    file_path=file_path,
                    duration_seconds=result.get("duration_seconds", 0.0),
                    file_size_bytes=result.get("file_size_bytes", 0),
                )
                session.add(audio_asset)
                await session.commit()
                await session.refresh(audio_asset)
                result["audio_id"] = audio_asset.id

        return result

    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run())
    finally:
        loop.close()
