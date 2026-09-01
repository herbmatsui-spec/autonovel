from __future__ import annotations

from sqlalchemy import select

from src.backend.database.models import Illustration
from src.backend.database.repositories.base import BaseRepository
from src.services.errors import retry_on_lock

"""
database/repositories/illustration.py - 挿絵(Illustrations)データ操作用のリポジトリ
"""


class IllustrationRepository(BaseRepository):
    """Illustrationsテーブルに関するDB操作をまとめたリポジトリ"""

    @retry_on_lock()
    async def create_illustration(
        self,
        book_id: int,
        illustration_type: str,
        image_url: str,
        prompt: str = "",
        episode_number: int | None = None,
        character_id: int | None = None,
        model: str = "imagen-4.0-fast-generate-001",
        safety_level: str = "BLOCK_SOME",
        generation_time_ms: int = 0,
    ) -> int:
        row = Illustration(
            book_id=book_id,
            illustration_type=illustration_type,
            episode_number=episode_number,
            character_id=character_id,
            model=model,
            safety_level=safety_level,
            prompt=prompt,
            image_url=image_url,
            generation_time_ms=generation_time_ms,
        )
        self.session.add(row)
        await self.session.flush()
        return row.id

    @retry_on_lock()
    async def list_illustrations(
        self, book_id: int, illustration_type: str | None = None
    ) -> list[Illustration]:
        stmt = select(Illustration).where(Illustration.book_id == book_id)
        if illustration_type:
            stmt = stmt.where(Illustration.illustration_type == illustration_type)
        stmt = stmt.order_by(Illustration.id.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
