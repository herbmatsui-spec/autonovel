from typing import Optional
from sqlalchemy import select
from src.backend.database.repositories.base import BaseRepository
from src.backend.database.models import PDCAHistorySnapshot

class PDCAHistoryRepository(BaseRepository[PDCAHistorySnapshot]):
    @property
    def model_class(self) -> type[PDCAHistorySnapshot]:
        return PDCAHistorySnapshot

    async def get_by_chapter(self, book_id: int, chapter_number: int) -> list[PDCAHistorySnapshot]:
        """特定の章のPDCA履歴をすべて取得する"""
        query = (
            select(PDCAHistorySnapshot)
            .where(
                PDCAHistorySnapshot.book_id == book_id,
                PDCAHistorySnapshot.chapter_number == chapter_number
            )
            .order_by(PDCAHistorySnapshot.cycle_number)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_latest_for_chapter(self, book_id: int, chapter_number: int) -> Optional[PDCAHistorySnapshot]:
        """特定の章の最新のPDCAスナップショットを取得する"""
        query = (
            select(PDCAHistorySnapshot)
            .where(
                PDCAHistorySnapshot.book_id == book_id,
                PDCAHistorySnapshot.chapter_number == chapter_number
            )
            .order_by(PDCAHistorySnapshot.cycle_number.desc())
            .limit(1)
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
