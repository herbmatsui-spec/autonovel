from __future__ import annotations
from pydantic import BaseModel, Field

class RefinementDetail(BaseModel):
    original_phrase: str
    refined_phrase: str
    reason: str  # 例: "感情説明から身体反応描写へ変更"

class ProseRefineResult(BaseModel):
    refined_text: str
    modifications: list[RefinementDetail] = Field(default_factory=list)
    total_fixes_count: int = 0
    latency_ms: float = 0.0