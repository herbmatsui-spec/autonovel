from typing import List, Optional
from pydantic import BaseModel, Field

class ConflictItemSchema(BaseModel):
    category: str = Field(..., description="カテゴリ (rhythm, dialogue, cliche, hook, character)")
    severity: str = Field(..., description="重要度 (critical, high, medium, low)")
    title: str = Field(..., description="指摘タイトル")
    description: str = Field(..., description="詳細説明")
    field_path: Optional[str] = None
    current_value: Optional[str] = None
    suggested_value: Optional[str] = None
    evidence_past: str = ""
    evidence_current: str = ""
    constraint_for_next: str = ""
    confidence: float = 0.9

class QualitativeAudit(BaseModel):
    hook_score: float = Field(..., ge=0.0, le=100.0, description="読者引き込み度")
    emotional_score: float = Field(..., ge=0.0, le=100.0, description="感情曲線の自然さ")
    character_consistency: float = Field(..., ge=0.0, le=100.0, description="キャラ言動の一貫性")
    overall_score: float = Field(..., ge=0.0, le=100.0, description="定性総合評価")
    critique: str = Field(default="", description="主要講評")
    actionable_patch: str | None = Field(default=None, description="推奨局所修正パッチ")

class UnifiedAuditReport(BaseModel):
    is_acceptable: bool
    final_score: float
    quantitative_score: float
    qualitative: QualitativeAudit
    detected_cliches: list[str] = Field(default_factory=list)
    dialogue_ratio: float = 0.0
    conflicts: list[ConflictItemSchema] = Field(default_factory=list)
