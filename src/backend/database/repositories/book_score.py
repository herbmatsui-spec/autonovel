from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.database.repositories.base import BaseRepository
from src.infrastructure.database.models.book_score import BookScore


class BookScoreRepository(BaseRepository[BookScore]):
    @property
    def model_class(self) -> type[BookScore]:
        return BookScore

    async def get_latest(self, book_id: int, chapter_number: int) -> Optional[BookScore]:
        result = await self.session.execute(
            select(BookScore)
            .where(BookScore.book_id == book_id)
            .where(BookScore.chapter_number == chapter_number)
            .order_by(BookScore.evaluated_at.desc())
        )
        return result.scalars().first()

    async def get_all_for_book(self, book_id: int) -> list[BookScore]:
        result = await self.session.execute(
            select(BookScore)
            .where(BookScore.book_id == book_id)
            .order_by(BookScore.chapter_number)
        )
        return list(result.scalars().all())