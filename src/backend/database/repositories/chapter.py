from __future__ import annotations

"""
database/repo_chapter.py - チャプター(Chapters)本文データ操作用のリポジトリMixin
"""
import json
import re
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import delete, or_, select, update

from services.errors import retry_on_lock
from src.backend.database.models import Chapter

if TYPE_CHECKING:
    from src.models import ChapterDbModel


from src.backend.database.repositories.base import BaseRepository


class ChapterRepository(BaseRepository):
    """Chaptersテーブルに関するDB操作をまとめたMixin"""
    @retry_on_lock()
    async def create_chapter(
        self, book_id: int, ep_num: int, title: str, content: str, summary: str,
        killer_phrase: Optional[str], ai_insight: str, world_state: Any,
        trinity_review_log: Any, created_at: str, tension_delta: int = 0, qol_delta: int = 0, branch_id: int = 1
    ) -> None:
        result = await self.session.execute(
            select(Chapter).where(Chapter.branch_id == branch_id).where(Chapter.ep_num == ep_num)
        )
        ch = result.scalar_one_or_none()
        if not ch:
            ch = Chapter(branch_id=branch_id, ep_num=ep_num)
            self.session.add(ch)
        ch.book_id = book_id
        ch.title = title
        ch.content = content
        ch.summary = summary if isinstance(summary, str) else json.dumps(summary, ensure_ascii=False)
        ch.killer_phrase = killer_phrase
        ch.ai_insight = ai_insight
        ch.world_state = json.dumps(world_state, ensure_ascii=False) if isinstance(world_state, (dict, list)) else (world_state or "{}")
        ch.trinity_review_log = json.dumps(trinity_review_log, ensure_ascii=False) if isinstance(trinity_review_log, (dict, list)) else (trinity_review_log or "{}")
        ch.created_at = created_at
        ch.tension_delta = tension_delta
        ch.qol_delta = qol_delta
    async def get_chapter(self, branch_id: int, ep_num: int) -> Optional['ChapterDbModel']:
        result = await self.session.execute(
            select(Chapter).where(Chapter.branch_id == branch_id).where(Chapter.ep_num == ep_num)
        )
        ch = result.scalar_one_or_none()
        if not ch:
            return None
        from src.models import ChapterDbModel
        return ChapterDbModel(**self._parse_row(self._to_dict(ch), ['world_state', 'trinity_review_log', 'summary']))
    async def get_chapters_before(self, branch_id: int, ep_num: int) -> List['ChapterDbModel']:
        result = await self.session.execute(
            select(Chapter)
            .where(Chapter.branch_id == branch_id)
            .where(Chapter.ep_num < ep_num)
            .order_by(Chapter.ep_num.desc())
        )
        chaps = result.scalars().all()
        from src.models import ChapterDbModel
        return [ChapterDbModel(**self._parse_row(self._to_dict(c), ['world_state', 'trinity_review_log', 'summary'])) for c in chaps]
    async def get_all_non_anchor_chapters(self, book_id_or_branch_id: int, branch_id: Optional[int] = None, order_by: str = "ep_num", limit: Optional[int] = None) -> List['ChapterDbModel']:
        target_branch_id = branch_id if branch_id is not None else book_id_or_branch_id
        stmt = select(Chapter).where(Chapter.branch_id == target_branch_id)
        if "desc" in order_by.lower():
            stmt = stmt.order_by(Chapter.ep_num.desc())
        else:
            stmt = stmt.order_by(Chapter.ep_num)
        if limit:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        chaps = result.scalars().all()
        from src.models import ChapterDbModel
        return [ChapterDbModel(**self._parse_row(self._to_dict(c), ['world_state', 'trinity_review_log', 'summary'])) for c in chaps]
    @retry_on_lock()
    async def delete_chapter(self, book_id_or_branch_id: int, ep_num: int, branch_id: Optional[int] = None) -> None:
        target_branch_id = branch_id if branch_id is not None else book_id_or_branch_id
        await self.session.execute(
            delete(Chapter).where(Chapter.branch_id == target_branch_id).where(Chapter.ep_num == ep_num)
        )
    @retry_on_lock()
    async def update_chapter_content(self, branch_id: int, ep_num: int, content: str) -> None:
        await self.session.execute(
            update(Chapter)
            .where(Chapter.branch_id == branch_id)
            .where(Chapter.ep_num == ep_num)
            .values(content=content)
        )

    @retry_on_lock()
    async def update_chapter_candidates(self, branch_id: int, ep_num: int, candidates: List[Any]) -> None:
        """チャプターの候補案のみを更新する"""
        await self.session.execute(
            update(Chapter)
            .where(Chapter.branch_id == branch_id)
            .where(Chapter.ep_num == ep_num)
            .values(candidates=json.dumps(candidates, ensure_ascii=False))
        )

    async def get_relevant_past_logs(
        self,
        branch_id: int,
        current_ep: int,
        query_text: str = "",
        top_k: int = 5,
    ) -> str:
        """【強化版RAG機能】現在のプロットに含まれるキーワードに基づき、過去の重要ログを抽出する。"""
        if not query_text: return ""
        keywords = re.findall(r'[一-龠々]{2,}|[ァ-ヶー]{2,}', query_text)
        if not keywords: return ""
        stmt = select(Chapter).where(Chapter.branch_id == branch_id).where(Chapter.ep_num < current_ep)
        like_clauses = [Chapter.content.like(f"%{k}%") for k in keywords[:5]]
        stmt = stmt.where(or_(*like_clauses))
        stmt = stmt.order_by(Chapter.ep_num.desc()).limit(top_k)
        result = await self.session.execute(stmt)
        chaps = result.scalars().all()

        if not chaps: return ""

        res = "【過去の関連文脈（RAG）】\n"
        for c in chaps:
            res += f"- 第{c.ep_num}話: {c.summary} (重要事項: {c.ai_insight})\n"
        return res
