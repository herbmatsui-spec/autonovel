"""Audit repository interface."""

from __future__ import annotations
from typing import Protocol, Optional, List, runtime_checkable
from src.domain.entities.audit import AuditFinding, AuditResult
from src.domain.value_objects.ids import AuditId, NovelId
from src.domain.entities.audit import AuditStatus, AuditType


@runtime_checkable
class IAuditRepository(Protocol):
    """Audit repository interface."""

    async def get_result_by_id(self, result_id: AuditId) -> Optional[AuditResult]:
        """Get audit result by ID."""
        ...

    async def save_result(self, result: AuditResult) -> AuditResult:
        """Save audit result (insert or update)."""
        ...

    async def list_results_by_novel(
        self,
        novel_id: NovelId,
        limit: int = 100,
        offset: int = 0,
        audit_type: Optional[AuditType] = None,
    ) -> List[AuditResult]:
        """List audit results by novel."""
        ...

    async def list_results_by_episode(
        self,
        novel_id: NovelId,
        episode_number: int,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditResult]:
        """List audit results by episode."""
        ...

    async def count_results_by_novel(
        self,
        novel_id: NovelId,
        audit_type: Optional[AuditType] = None,
    ) -> int:
        """Count audit results for a novel."""
        ...

    async def get_latest_result(
        self,
        novel_id: NovelId,
        audit_type: Optional[AuditType] = None,
    ) -> Optional[AuditResult]:
        """Get latest audit result for novel."""
        ...

    async def delete_result(self, result_id: AuditId) -> bool:
        """Delete audit result by ID. Returns True if deleted."""
        ...

    # AuditFinding methods
    async def get_finding(self, finding_id: AuditId) -> Optional[AuditFinding]:
        """Get audit finding by ID."""
        ...

    async def save_finding(self, finding: AuditFinding) -> AuditFinding:
        """Save audit finding (insert or update)."""
        ...

    async def list_findings_by_result(
        self,
        result_id: AuditId,
        limit: int = 100,
        offset: int = 0,
        status: Optional[AuditStatus] = None,
    ) -> List[AuditFinding]:
        """List findings by audit result."""
        ...

    async def count_findings_by_result(
        self,
        result_id: AuditId,
        status: Optional[AuditStatus] = None,
    ) -> int:
        """Count findings in an audit result."""
        ...

    async def get_findings_by_severity(
        self,
        novel_id: NovelId,
        severity: str,
        limit: int = 100,
    ) -> List[AuditFinding]:
        """Get findings by severity across all audits for a novel."""
        ...

    async def get_open_findings(
        self,
        novel_id: NovelId,
        limit: int = 100,
    ) -> List[AuditFinding]:
        """Get all open findings for a novel."""
        ...