from __future__ import annotations
from typing import List
from pydantic import Field
from src.domain.schemas.base import AutoNovelBaseSchema

class AuditIssue(AutoNovelBaseSchema):
    rule_id: str
    severity: str = "warning"  # error, warning, info
    message: str
    line_number: int = 0
    suggested_fix: str = ""

class StaticAuditResult(AutoNovelBaseSchema):
    passed: bool
    execution_time_ms: float = 0.0
    issues: List[AuditIssue] = Field(default_factory=list)

class QualitativeAuditResult(AutoNovelBaseSchema):
    score: int = Field(..., ge=0, le=100)
    pacing_comment: str = ""
    character_voice_comment: str = ""
    entertaining_hook_comment: str = ""
    suggested_patch: str = ""

class IntegratedAuditReport(AutoNovelBaseSchema):
    static_audit: StaticAuditResult
    qualitative_audit: QualitativeAuditResult
    final_decision: str = "pass"  # pass, patch_required, reject
