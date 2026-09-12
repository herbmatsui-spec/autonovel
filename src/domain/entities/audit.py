"""Audit domain entity."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from uuid import uuid4
from enum import Enum

from src.domain.value_objects.ids import NovelId, AuditId
from src.domain.value_objects.metadata import AuditMetadata


class AuditCategory(Enum):
    """Audit finding category."""
    LOGIC = "logic"
    STYLE = "style"
    CHARACTER = "character"
    WORLD = "world"
    PACING = "pacing"
    PLOT_HOLE = "plot_hole"
    INCONSISTENCY = "inconsistency"
    CONTINUITY = "continuity"
    TONE = "tone"
    GRAMMAR = "grammar"


class AuditSeverity(Enum):
    """Audit finding severity."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AuditStatus(Enum):
    """Audit finding status."""
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


class AuditType(Enum):
    """Audit type."""
    LOGICAL = "logical"
    STYLE = "style"
    COMPREHENSIVE = "comprehensive"
    QUICK = "quick"


@dataclass
class AuditFinding:
    """Individual audit finding."""
    id: AuditId
    category: AuditCategory
    severity: AuditSeverity
    description: str
    evidence_past: str = ""
    evidence_current: str = ""
    constraint_for_next: str = ""
    status: AuditStatus = AuditStatus.OPEN
    resolved_note: str = ""
    episode_number: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

    def __post_init__(self) -> None:
        if not self.description.strip():
            raise ValueError("Description cannot be empty")
        if self.episode_number < 0:
            raise ValueError("Episode number cannot be negative")

    @classmethod
    def create(
        cls,
        category: AuditCategory,
        severity: AuditSeverity,
        description: str,
        episode_number: int,
        evidence_past: str = "",
        evidence_current: str = "",
        constraint_for_next: str = "",
    ) -> AuditFinding:
        """Factory method to create a new finding."""
        return cls(
            id=AuditId.generate(),
            category=category,
            severity=severity,
            description=description,
            evidence_past=evidence_past,
            evidence_current=evidence_current,
            constraint_for_next=constraint_for_next,
            episode_number=episode_number,
        )

    def acknowledge(self) -> None:
        """Acknowledge the finding."""
        self.status = AuditStatus.ACKNOWLEDGED

    def start_resolution(self) -> None:
        """Start working on resolution."""
        self.status = AuditStatus.IN_PROGRESS

    def resolve(self, note: str, resolved_by: str) -> None:
        """Mark as resolved."""
        self.status = AuditStatus.RESOLVED
        self.resolved_note = note
        self.resolved_at = datetime.now()
        self.resolved_by = resolved_by

    def reject(self, note: str) -> None:
        """Reject the finding."""
        self.status = AuditStatus.REJECTED
        self.resolved_note = note

    def defer(self, note: str = "") -> None:
        """Defer the finding."""
        self.status = AuditStatus.DEFERRED
        self.resolved_note = note

    def is_critical(self) -> bool:
        """Check if finding is critical severity."""
        return self.severity == AuditSeverity.CRITICAL

    def is_open(self) -> bool:
        """Check if finding is still open."""
        return self.status in (AuditStatus.OPEN, AuditStatus.ACKNOWLEDGED, AuditStatus.IN_PROGRESS)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "category": self.category.value,
            "severity": self.severity.value,
            "description": self.description,
            "evidence_past": self.evidence_past,
            "evidence_current": self.evidence_current,
            "constraint_for_next": self.constraint_for_next,
            "status": self.status.value,
            "resolved_note": self.resolved_note,
            "episode_number": self.episode_number,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
        }


@dataclass
class AuditResult:
    """Audit result aggregate - contains all findings for an episode."""
    id: AuditId
    novel_id: NovelId
    episode_number: int
    audit_type: AuditType
    findings: List[AuditFinding] = field(default_factory=list)
    summary: str = ""
    overall_score: int = 100  # 0-100, lower = more issues
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.episode_number < 1:
            raise ValueError("Episode number must be positive")
        if not 0 <= self.overall_score <= 100:
            raise ValueError("Overall score must be between 0 and 100")

    @classmethod
    def create(
        cls,
        novel_id: NovelId,
        episode_number: int,
        audit_type: AuditType,
    ) -> AuditResult:
        """Factory method to create a new audit result."""
        return cls(
            id=AuditId.generate(),
            novel_id=novel_id,
            episode_number=episode_number,
            audit_type=audit_type,
            findings=[],
            summary="",
            overall_score=100,
        )

    def add_finding(self, finding: AuditFinding) -> None:
        """Add a finding to this audit."""
        if finding.episode_number != self.episode_number:
            raise ValueError("Finding episode must match audit episode")
        self.findings.append(finding)
        self._recalculate_score()

    def remove_finding(self, finding_id: AuditId) -> bool:
        """Remove a finding by ID."""
        for i, f in enumerate(self.findings):
            if f.id == finding_id:
                self.findings.pop(i)
                self._recalculate_score()
                return True
        return False

    def get_findings_by_category(self, category: AuditCategory) -> List[AuditFinding]:
        """Get findings filtered by category."""
        return [f for f in self.findings if f.category == category]

    def get_findings_by_severity(self, severity: AuditSeverity) -> List[AuditFinding]:
        """Get findings filtered by severity."""
        return [f for f in self.findings if f.severity == severity]

    def get_open_findings(self) -> List[AuditFinding]:
        """Get all open findings."""
        return [f for f in self.findings if f.is_open()]

    def get_critical_findings(self) -> List[AuditFinding]:
        """Get all critical findings."""
        return [f for f in self.findings if f.is_critical()]

    def _recalculate_score(self) -> None:
        """Recalculate overall score based on findings."""
        if not self.findings:
            self.overall_score = 100
            return

        # Weight by severity
        severity_weights = {
            AuditSeverity.CRITICAL: 30,
            AuditSeverity.HIGH: 15,
            AuditSeverity.MEDIUM: 8,
            AuditSeverity.LOW: 3,
            AuditSeverity.INFO: 1,
        }

        total_deduction = sum(
            severity_weights.get(f.severity, 5)
            for f in self.findings
            if f.is_open()
        )

        self.overall_score = max(0, 100 - total_deduction)

    def complete(self, summary: str) -> None:
        """Mark audit as complete."""
        self.summary = summary
        self.completed_at = datetime.now()
        self._recalculate_score()

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "id": str(self.id),
            "novel_id": str(self.novel_id),
            "episode_number": self.episode_number,
            "audit_type": self.audit_type.value,
            "findings": [f.to_dict() for f in self.findings],
            "summary": self.summary,
            "overall_score": self.overall_score,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AuditResult):
            return NotImplemented
        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)


__all__ = [
    "AuditFinding",
    "AuditResult",
    "AuditCategory",
    "AuditSeverity",
    "AuditStatus",
    "AuditType",
]