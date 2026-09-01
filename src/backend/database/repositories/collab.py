"""
database/repositories/collab.py - 共同執筆・レビューコメント用リポジトリ
"""

from __future__ import annotations

from typing import List, Optional

from sqlalchemy import select

from src.backend.database.models import Comment, ProjectMember
from src.services.errors import retry_on_lock


class CollabRepository:
    def __init__(self, session):
        self.session = session

    # ---- Members ----
    @retry_on_lock()
    async def add_member(self, book_id: int, user_name: str, role: str = "viewer") -> int:
        member = ProjectMember(book_id=book_id, user_name=user_name, role=role)
        self.session.add(member)
        await self.session.flush()
        return member.id

    @retry_on_lock()
    async def list_members(self, book_id: int) -> List[ProjectMember]:
        result = await self.session.execute(
            select(ProjectMember).where(ProjectMember.book_id == book_id).order_by(ProjectMember.id)
        )
        return list(result.scalars().all())

    @retry_on_lock()
    async def remove_member(self, member_id: int) -> int:
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(ProjectMember).where(ProjectMember.id == member_id)
        )
        return result.rowcount

    # ---- Comments ----
    @retry_on_lock()
    async def add_comment(
        self,
        book_id: int,
        chapter_ep: int,
        author_name: str,
        content: str,
        anchor_text: str = "",
        parent_id: Optional[int] = None,
    ) -> int:
        comment = Comment(
            book_id=book_id,
            chapter_ep=chapter_ep,
            anchor_text=anchor_text,
            author_name=author_name,
            content=content,
            parent_id=parent_id,
            resolved=False,
        )
        self.session.add(comment)
        await self.session.flush()
        return comment.id

    @retry_on_lock()
    async def list_comments(self, book_id: int, chapter_ep: Optional[int] = None) -> List[Comment]:
        stmt = select(Comment).where(Comment.book_id == book_id)
        if chapter_ep is not None:
            stmt = stmt.where(Comment.chapter_ep == chapter_ep)
        stmt = stmt.order_by(Comment.created_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    @retry_on_lock()
    async def resolve_comment(self, comment_id: int, resolved: bool = True) -> int:
        from sqlalchemy import update

        result = await self.session.execute(
            update(Comment).where(Comment.id == comment_id).values(resolved=resolved)
        )
        return result.rowcount

    @retry_on_lock()
    async def delete_comment(self, comment_id: int) -> int:
        from sqlalchemy import delete

        result = await self.session.execute(delete(Comment).where(Comment.id == comment_id))
        return result.rowcount
