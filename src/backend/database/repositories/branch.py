from __future__ import annotations

"""
database/repo_branch.py - ブランチ(Branches)データ操作用のリポジトリMixin
"""
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select, update

from src.backend.database.models import Book, Branch, BranchPlaySession, Chapter, Plot

if TYPE_CHECKING:
    from src.models import BranchDbModel


from src.backend.database.repositories.base import BaseRepository


class BranchRepository(BaseRepository):
    """Branchesテーブルに関するDB操作をまとめたMixin"""

    async def create_branch(
        self, book_id: int, name: str, parent_id: int | None = None, fork_ep_num: int = 0
    ) -> int:
        """新しいブランチを作し、必要に応じて親ブランチからデータをコピーする"""
        print(f"[repo] session bind URL: {self.session.bind.url}", flush=True)
        branch = Branch(
            book_id=book_id,
            name=name,
            parent_id=parent_id,
            fork_ep_num=fork_ep_num,
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
                c_dict["branch_id"] = branch_id
                self.session.add(Chapter(**c_dict))

        return branch_id

    async def get_branches(self, book_id: int) -> list[BranchDbModel]:
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

    async def get_branch(self, branch_id: int) -> BranchDbModel | None:
        """単一ブランチ取得."""
        result = await self.session.execute(select(Branch).where(Branch.id == branch_id))
        b = result.scalar_one_or_none()
        if not b:
            return None
        from src.models import BranchDbModel

        return BranchDbModel(**self._to_dict(b))

    async def get_branch_tree(self, book_id: int) -> list[BranchDbModel]:
        """書籍の全ブランチをツリー順に取得 (parent_id → child の深さ優先)."""
        result = await self.session.execute(
            select(Branch)
            .where(Branch.book_id == book_id)
            .order_by(Branch.parent_id, Branch.created_at)
        )
        branches = result.scalars().all()
        from src.models import BranchDbModel

        return [BranchDbModel(**self._to_dict(b)) for b in branches]

    async def save_branch_graph(self, branch_id: int, graph_json: dict) -> None:
        """IF グラフをブランチに保存."""
        await self.session.execute(
            update(Branch).where(Branch.id == branch_id).values(graph_json=graph_json)
        )

    async def load_branch_graph(self, branch_id: int) -> dict | None:
        """IF グラフをブランチから読み出し."""
        result = await self.session.execute(select(Branch.graph_json).where(Branch.id == branch_id))
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # BranchPlaySession CRUD (Episode 3 向け S25-S30 の先行実装)
    # ------------------------------------------------------------------

    async def create_play_session(
        self, session_id: str, book_id: int, branch_id: int, current_node_id: str | None = None
    ) -> None:
        session = BranchPlaySession(
            id=session_id,
            book_id=book_id,
            branch_id=branch_id,
            current_node_id=current_node_id,
            context_json={},
            save_points_json=[],
            status="active",
        )
        self.session.add(session)
        await self.session.flush()

    async def get_play_session(self, session_id: str) -> BranchPlaySession | None:
        result = await self.session.execute(
            select(BranchPlaySession).where(BranchPlaySession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def update_play_session_state(
        self,
        session_id: str,
        current_node_id: str | None,
        context_json: dict,
        save_points_json: list,
    ) -> None:
        await self.session.execute(
            update(BranchPlaySession)
            .where(BranchPlaySession.id == session_id)
            .values(
                current_node_id=current_node_id,
                context_json=context_json,
                save_points_json=save_points_json,
            )
        )

    async def end_play_session(self, session_id: str, status: str = "completed") -> None:
        await self.session.execute(
            update(BranchPlaySession)
            .where(BranchPlaySession.id == session_id)
            .values(status=status)
        )

    async def list_play_sessions(
        self, book_id: int, branch_id: int | None = None
    ) -> list[BranchPlaySession]:
        """書籍配下のセッション一覧. branch_id 指定時はそのブランチのみ."""
        stmt = select(BranchPlaySession).where(BranchPlaySession.book_id == book_id)
        if branch_id is not None:
            stmt = stmt.where(BranchPlaySession.branch_id == branch_id)
        stmt = stmt.order_by(BranchPlaySession.updated_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_play_session_state_optimistic(
        self,
        session_id: str,
        expected_version: int,
        current_node_id: str | None,
        context_json: dict,
        save_points_json: list,
    ) -> bool:
        """version 一致を条件にした楽観ロック付き UPDATE.

        Returns True if updated, False if version mismatch.
        UPDATE 成功時に version を +1 する。
        """
        result = await self.session.execute(
            update(BranchPlaySession)
            .where(BranchPlaySession.id == session_id)
            .where(BranchPlaySession.version == expected_version)
            .values(
                current_node_id=current_node_id,
                context_json=context_json,
                save_points_json=save_points_json,
                version=expected_version + 1,
            )
        )
        return (result.rowcount or 0) > 0
