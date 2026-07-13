from __future__ import annotations

"""
database/repo_branch.py - ブランチ(Branches)データ操作用のリポジトリMixin
"""
import time
from typing import List, Optional

from sqlalchemy import select, update

from src.backend.database.core import retry_with_logging
from src.backend.database.models import Book, Branch, Chapter, Plot
from src.models import BranchDbModel


class BranchRepositoryMixin:
    """Branchesテーブルに関するDB操作をまとめたMixin"""

    @retry_with_logging()
    async def create_branch(self, book_id: int, name: str, parent_id: Optional[int] = None, fork_ep_num: int = 0) -> int:
        """新しいブランチを作成し、必要に応じて親ブランチからデータをコピーする"""
        async with self._get_session() as session:
            branch = Branch(
                book_id=book_id,
                name=name,
                parent_id=parent_id,
                fork_ep_num=fork_ep_num,
                created_at=time.strftime('%Y-%m-%dT%H:%M:%S')
            )
            session.add(branch)
            await session.flush()
            branch_id = branch.id

            if parent_id and fork_ep_num > 0:
                # プロットのコピー
                plot_result = await session.execute(
                    select(Plot).where(Plot.branch_id == parent_id).where(Plot.ep_num <= fork_ep_num)
                )
                parent_plots = plot_result.scalars().all()
                for p in parent_plots:
                    p_dict = {c.name: getattr(p, c.name) for c in p.__table__.columns}
                    p_dict['branch_id'] = branch_id
                    session.add(Plot(**p_dict))

                # チャプターのコピー
                chap_result = await session.execute(
                    select(Chapter).where(Chapter.branch_id == parent_id).where(Chapter.ep_num <= fork_ep_num)
                )
                parent_chaps = chap_result.scalars().all()
                for c in parent_chaps:
                    c_dict = {c_col.name: getattr(c, c_col.name) for c_col in c.__table__.columns}
                    c_dict['branch_id'] = branch_id
                    session.add(Chapter(**c_dict))

            return branch_id

    @retry_with_logging()
    async def get_branches(self, book_id: int) -> List[BranchDbModel]:
        async with self._get_session() as session:
            result = await session.execute(
                select(Branch).where(Branch.book_id == book_id).order_by(Branch.created_at)
            )
            branches = result.scalars().all()
            return [BranchDbModel(**self._to_dict(b)) for b in branches]

    @retry_with_logging()
    async def update_book_current_branch(self, book_id: int, branch_id: int) -> None:
        async with self._get_session() as session:
            await session.execute(
                update(Book).where(Book.id == book_id).values(current_branch_id=branch_id)
            )

