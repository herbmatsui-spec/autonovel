from __future__ import annotations

"""
database/repo_book.py - 作品(Books)データ操作用のリポジトリMixin
"""
import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from sqlalchemy import delete, select, update

from services.errors import retry_on_lock
from src.backend.database.models import Book, Chapter, Plot

if TYPE_CHECKING:
    from src.models import BookDbModel

logger = logging.getLogger(__name__)


from src.backend.database.repositories.base import BaseRepository


class BookRepository(BaseRepository):
    """Booksテーブルに関するDB操作をまとめたMixin"""
    @retry_on_lock()
    async def create_book(self, title: str, genre: str, concept: str, synopsis: str,
                      target_eps: int, style_dna: dict, marketing_data: dict) -> int:
        book = Book(
            title=title,
            genre=genre,
            concept=concept,
            synopsis=synopsis,
            target_eps=target_eps,
            style_dna=json.dumps(style_dna, ensure_ascii=False),
            marketing_data=json.dumps(marketing_data, ensure_ascii=False),
            created_at=datetime.now()
        )
        self.session.add(book)
        await self.session.flush()
        return book.id
    async def get_book(self, book_id: int) -> Optional['BookDbModel']:
        result = await self.session.execute(select(Book).where(Book.id == book_id))
        book = result.scalar_one_or_none()
        if not book:
            return None
        d = self._to_dict(book)
        d = self._parse_row(d, ['style_dna', 'marketing_data'])
        from src.models import BookDbModel
        return BookDbModel(**d)
    async def get_all_books(self) -> List['BookDbModel']:
        result = await self.session.execute(select(Book).order_by(Book.id.desc()))
        books = result.scalars().all()
        from src.models import BookDbModel
        return [BookDbModel(**self._parse_row(self._to_dict(b), ['style_dna', 'marketing_data'])) for b in books]
    @retry_on_lock()
    async def update_book_cumulative_tension(self, book_id: int, tension: int) -> None:
        await self.session.execute(
            update(Book).where(Book.id == book_id).values(cumulative_tension=tension)
        )
    @retry_on_lock()
    async def update_book_cumulative_stress(self, book_id: int, stress: int) -> None:
        # stress is mapped to cumulative_tension
        await self.session.execute(
            update(Book).where(Book.id == book_id).values(cumulative_tension=stress)
        )
    @retry_on_lock()
    async def delete_book(self, book_id: int) -> None:
        await self.session.execute(
            delete(Book).where(Book.id == book_id)
        )
    @retry_on_lock()
    async def update_book_marketing_data(self, book_id: int, title: str, marketing_data: Dict[str, Any]) -> None:
        """作品名とマーケティングデータを更新する。既存のデータがある場合はマージを試みる。"""
        import traceback
        result = await self.session.execute(select(Book.marketing_data).where(Book.id == book_id))
        row_val = result.scalar_one_or_none()
        current_data = {}
        if row_val:
            try:
                current_data = json.loads(row_val) if isinstance(row_val, str) else row_val
            except Exception as e:
                logger.warning(f"Failed to parse marketing_data JSON: {e}\n{traceback.format_exc()}")

        merged = {**current_data, **marketing_data}
        await self.session.execute(
            update(Book).where(Book.id == book_id).values(
                title=title,
                marketing_data=json.dumps(merged, ensure_ascii=False)
            )
        )
    @retry_on_lock()
    async def update_book_target_eps(self, book_id: int, new_total_eps: int) -> None:
        """作品の目標話数を更新する"""
        await self.session.execute(
            update(Book).where(Book.id == book_id).values(target_eps=new_total_eps)
        )
    @retry_on_lock()
    async def recalculate_book_tension(self, book_id: int, branch_id: int = 1) -> int:
        """指定ブランチの全チャプターの tension_delta を合計して累積テンションを再計算し、DBを更新する"""
        result = await self.session.execute(select(Chapter.tension_delta).where(Chapter.branch_id == branch_id))
        rows = result.scalars().all()
        total_tension = sum(t or 0 for t in rows)
        await self.session.execute(
            update(Book).where(Book.id == book_id).values(cumulative_tension=total_tension)
        )
        return total_tension
    @retry_on_lock()
    async def recalculate_book_comfort(self, book_id: int, branch_id: int = 1) -> Tuple[int, int]:
        """指定ブランチの全チャプターの qol_delta を合計して累積QOLを再計算し、DBを更新する"""
        result = await self.session.execute(select(Chapter.qol_delta).where(Chapter.branch_id == branch_id))
        rows = result.scalars().all()
        total_qol = sum(q or 0 for q in rows)

        plot_result = await self.session.execute(
            select(Plot.state_integrity_score)
            .where(Plot.branch_id == branch_id)
            .order_by(Plot.ep_num.desc())
            .limit(1)
        )
        latest_plot_score = plot_result.scalar_one_or_none()
        integrity = latest_plot_score if latest_plot_score is not None else 100

        await self.session.execute(
            update(Book).where(Book.id == book_id).values(
                cumulative_qol=total_qol,
                sanctuary_integrity=integrity
            )
        )
        return total_qol, integrity
    @retry_on_lock()
    async def recalculate_book_cost(self, book_id: int, branch_id: int = 1) -> float:
        """最新のプロットから代償蓄積スコアを取得し、DBを更新する"""
        plot_result = await self.session.execute(
            select(Plot.cost_score)
            .where(Plot.branch_id == branch_id)
            .where(Plot.status == 'expanded')
            .order_by(Plot.ep_num.desc())
            .limit(1)
        )
        latest_plot_cost = plot_result.scalar_one_or_none()
        total_cost = latest_plot_cost if latest_plot_cost is not None else 0.0

        await self.session.execute(
            update(Book).where(Book.id == book_id).values(cumulative_cost=total_cost)
        )
        return total_cost

