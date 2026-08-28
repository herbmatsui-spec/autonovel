from __future__ import annotations

"""
database/repo_branch.py - ブランチ(Branches)データ操作用のリポジトリMixin
"""
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import select, update

from src.backend.database.models import Book, Branch, Chapter, Plot

if TYPE_CHECKING:
    from src.models import BranchDbModel


from src.backend.database.repositories.base import BaseRepository


class BranchRepository(BaseRepository):
    """Branchesテーブルに関するDB操作をまとめたMixin"""

    async def create_branch(
        self,
        book_id: int,
        name: str,
        parent_id: Optional[int] = None,
        fork_ep_num: int = 0,
        divergence_reason: str = "",
        what_if_snippet: Optional[str] = None,
    ) -> int:
        """新しいブランチを作成し、必要に応じて親ブランチからデータをコピーする"""
        branch = Branch(
            book_id=book_id,
            name=name,
            parent_id=parent_id,
            fork_ep_num=fork_ep_num,
            divergence_reason=divergence_reason or "",
            created_at=datetime.now(),
        )
        self.session.add(branch)
        await self.session.flush()
        branch_id = branch.id

        if parent_id and fork_ep_num > 0:
            # プロットのコピー
            plot_result = await self.session.execute(
                select(Plot).where(Plot.branch_id == parent_id).where(Plot.ep_num <= fork_ep_num)
            )
            parent_plots = plot_result.scalars().all()
            for p in parent_plots:
                p_dict = {c.name: getattr(p, c.name) for c in p.__table__.columns}
                p_dict.pop("id", None)
                p_dict["branch_id"] = branch_id
                self.session.add(Plot(**p_dict))

            # チャプターのコピー
            chap_result = await self.session.execute(
                select(Chapter)
                .where(Chapter.branch_id == parent_id)
                .where(Chapter.ep_num <= fork_ep_num)
            )
            parent_chaps = chap_result.scalars().all()
            for c in parent_chaps:
                c_dict = {c_col.name: getattr(c, c_col.name) for c_col in c.__table__.columns}
                c_dict.pop("id", None)
                c_dict["branch_id"] = branch_id
                self.session.add(Chapter(**c_dict))

        # What-If スニペットが指定されている場合、fork_ep_num + 1 の初期プロットをシード
        if what_if_snippet:
            next_ep = fork_ep_num + 1
            seeded_plot = Plot(
                book_id=book_id,
                branch_id=branch_id,
                ep_num=next_ep,
                title=f"{name} (Ep {next_ep})",
                summary=divergence_reason or f"What-If 分岐: {name}",
                thought_process=what_if_snippet,
                status="planned",
            )
            self.session.add(seeded_plot)

        await self.session.flush()
        return branch_id

    async def get_branches(self, book_id: int) -> List["BranchDbModel"]:
        result = await self.session.execute(
            select(Branch).where(Branch.book_id == book_id).order_by(Branch.created_at)
        )
        branches = result.scalars().all()
        from src.models import BranchDbModel

        return [BranchDbModel(**self._to_dict(b)) for b in branches]

    async def update_book_current_branch(self, book_id: int, branch_id: int) -> None:
        await self.session.execute(
            update(Book).where(Book.id == book_id).values(current_branch_id=branch_id)
        )
