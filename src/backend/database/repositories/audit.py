from __future__ import annotations

"""
database/repositories/audit.py - 監査Issueデータ操作用のリポジトリ
"""
import logging
from typing import List, Optional

from sqlalchemy import select, update

from src.backend.database.models import AuditIssue
from src.backend.database.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class AuditRepository(BaseRepository):
    """監査Issueに関するDB操作をまとめたリポジトリ"""

    async def create_audit_issue(
        self, book_id: int, ep_num: int, category: str, severity: str,
        description: str, evidence_past: str = "", evidence_current: str = "",
        constraint_for_next_ep: str = ""
    ) -> int:
        issue = AuditIssue(
            book_id=book_id,
            ep_num=ep_num,
            category=category,
            severity=severity,
            description=description,
            evidence_past=evidence_past,
            evidence_current=evidence_current,
            constraint_for_next_ep=constraint_for_next_ep,
            status="open"
        )
        self.session.add(issue)
        await self.session.flush()
        return issue.id

    async def get_issue(self, issue_id: int) -> Optional[AuditIssueDbModel]:
        result = await self.session.execute(select(AuditIssue).where(AuditIssue.id == issue_id))
        row = result.scalar_one_or_none()
        return self._to_dict(row) if row else None

    async def get_issues_by_book(self, book_id: int, status: Optional[str] = None) -> List[AuditIssueDbModel]:
        stmt = select(AuditIssue).where(AuditIssue.book_id == book_id)
        if status:
            stmt = stmt.where(AuditIssue.status == status)
        stmt = stmt.order_by(AuditIssue.id.desc())
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_dict(r) for r in rows]

    async def update_issue_status(self, issue_id: int, status: str, resolved_note: str = "") -> None:
        await self.session.execute(
            update(AuditIssue)
            .where(AuditIssue.id == issue_id)
            .values(status=status, resolved_note=resolved_note)
        )

