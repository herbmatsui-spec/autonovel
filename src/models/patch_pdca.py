from __future__ import annotations
from pydantic import BaseModel, Field

class ParagraphTarget(BaseModel):
    index: int = Field(..., description="段落インデックス (0始まり)")
    original_text: str
    issue_category: str  # 例: "emotional_flatness", "foreshadow_miss"
    directive: str       # 修正指示

class PatchRewriteResult(BaseModel):
    index: int
    patched_text: str
    confidence_score: float