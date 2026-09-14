"""Audit DTOs."""

from __future__ import annotations
from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, Field

MODEL_CONFIG_DEFAULTS = ConfigDict(populate_by_name=True, extra="allow", protected_namespaces=())


class AuditRequestDTO(BaseModel):
    """DTO for requesting an audit."""

    novel_id: str = Field(..., min_length=1)
    branch_id: str = Field(..., min_length=1)
    audit_type: Literal["logical", "style", "character", "bible", "full"] = "full"
    episode_range: Optional[tuple[int, int]] = None
    specific_checks: Optional[list[str]] = None
    include_suggestions: bool = Field(default=True)

    model_config = MODEL_CONFIG_DEFAULTS


class AuditFindingDTO(BaseModel):
    """DTO for audit finding."""

    id: str
    audit_id: str
    finding_type: str  # "inconsistency", "plot_hole", "character_break", "style_violation", "bible_conflict"
    severity: Literal["critical", "major", "minor", "info"]
    title: str
    description: str
    location: Optional[str] = None  # e.g., "Episode 5, Chapter 3"
    related_entities: list[str] = Field(default_factory=list)
    suggestion: Optional[str] = None
    auto_fixable: bool = Field(default=False)

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, finding: "AuditFinding") -> "AuditFindingDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(finding.id),
            audit_id=str(finding.audit_id),
            finding_type=finding.finding_type,
            severity=finding.severity,
            title=finding.title,
            description=finding.description,
            location=finding.location,
            related_entities=finding.related_entities,
            suggestion=finding.suggestion,
            auto_fixable=finding.auto_fixable,
        )


class AuditResponseDTO(BaseModel):
    """DTO for audit response."""

    id: str
    novel_id: str
    branch_id: str
    audit_type: str
    status: Literal["pending", "running", "completed", "failed"]
    overall_score: Optional[float] = None
    findings: list[AuditFindingDTO] = Field(default_factory=list)
    summary: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, audit: "AuditResult") -> "AuditResponseDTO":
        """Create DTO from domain entity."""
        return cls(
            id=str(audit.id),
            novel_id=str(audit.novel_id),
            branch_id=str(audit.branch_id),
            audit_type=audit.audit_type,
            status=audit.status,
            overall_score=audit.overall_score,
            findings=[AuditFindingDTO.from_entity(f) for f in audit.findings],
            summary=audit.summary,
            started_at=audit.started_at,
            completed_at=audit.completed_at,
            created_at=audit.created_at,
        )


class AuditListItemDTO(BaseModel):
    """DTO for audit list item (lightweight)."""

    id: str
    novel_id: str
    branch_id: str
    audit_type: str
    status: str
    overall_score: Optional[float] = None
    findings_count: int
    critical_count: int
    major_count: int
    created_at: datetime

    model_config = MODEL_CONFIG_DEFAULTS

    @classmethod
    def from_entity(cls, audit: "AuditResult") -> "AuditListItemDTO":
        """Create DTO from domain entity."""
        severity_counts = {"critical": 0, "major": 0, "minor": 0, "info": 0}
        for f in audit.findings:
            if f.severity in severity_counts:
                severity_counts[f.severity] += 1
        return cls(
            id=str(audit.id),
            novel_id=str(audit.novel_id),
            branch_id=str(audit.branch_id),
            audit_type=audit.audit_type,
            status=audit.status,
            overall_score=audit.overall_score,
            findings_count=len(audit.findings),
            critical_count=severity_counts["critical"],
            major_count=severity_counts["major"],
            created_at=audit.created_at,
        )


class AuditHistoryFilterDTO(BaseModel):
    """DTO for filtering audit history."""

    novel_id: Optional[str] = None
    branch_id: Optional[str] = None
    audit_type: Optional[str] = None
    status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None

    model_config = MODEL_CONFIG_DEFAULTS