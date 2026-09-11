from typing import Optional
from sqlalchemy import select, func
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

    async def save(self, score: BookScore) -> None:
        self.add(score)

    async def get_all_for_book(self, book_id: int) -> list[BookScore]:
        result = await self.session.execute(
            select(BookScore)
            .where(BookScore.book_id == book_id)
            .order_by(BookScore.chapter_number)
        )
        return list(result.scalars().all())

    async def get_history_for_book(self, book_id: int) -> list[BookScore]:
        """
        書籍の全章について、それぞれの最新の BookScore を取得し、
        章番号順にソートして返す。
        """
        # 各章の最新の evaluated_at を取得するサブクエリ
        subquery = (
            select(BookScore.chapter_number, func.max(BookScore.evaluated_at).label("max_at"))
            .where(BookScore.book_id == book_id)
            .group_by(BookScore.chapter_number)
            .subquery()
        )

        # サブクエリと結合して、最新のレコードのみを抽出
        query = (
            select(BookScore)
            .join(subquery, (BookScore.chapter_number == subquery.c.chapter_number) &
                            (BookScore.evaluated_at == subquery.c.max_at))
            .where(BookScore.book_id == book_id)
            .order_by(BookScore.chapter_number)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_genre_benchmarks(self) -> dict[str, dict[str, float]]:
        """
        ジャンルごとの5次元スコアの平均値を算出する。
        """
        from src.backend.database.models import Book
        from sqlalchemy import func

        query = (
            select(
                Book.genre,
                func.avg(BookScore.structure_score).label("structure"),
                func.avg(BookScore.coherency_score).label("coherency"),
                func.avg(BookScore.factual_grounding_score).label("factual"),
                func.avg(BookScore.visual_textual_synergy_score).label("visual"),
                func.avg(BookScore.reader_experience_score).label("experience"),
            )
            .join(Book, Book.id == BookScore.book_id)
            .group_by(Book.genre)
        )

        result = await self.session.execute(query)
        rows = result.all()

        benchmarks = {}
        for row in rows:
            benchmarks[row.genre] = {
                "structure": round(row.structure or 0.0, 2),
                "coherency": round(row.coherency or 0.0, 2),
                "factual": round(row.factual or 0.0, 2),
                "visual": round(row.visual or 0.0, 2),
                "experience": round(row.experience or 0.0, 2),
            }
        return benchmarks