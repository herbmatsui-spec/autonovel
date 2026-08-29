"""consistency/findings.py - Finding データモデル"""
from typing import List, Optional
from pydantic import BaseModel, Field


class Evidence(BaseModel):
    source: str = ""  # e.g., "第5章 L120"
    text: str = ""


class Finding(BaseModel):
    category: str  # foreshadowing | timeline | character | world | duplicate
    severity: str = "medium"  # high | medium | low
    description: str = ""
    evidence: List[Evidence] = Field(default_factory=list)
    suggestion: str = ""
    is_intentional: bool = False
    intentional_reason: Optional[str] = None

    def key(self) -> str:
        """一意キー（重複排除・却下管理用）"""
        return f"{self.category}:{self.description[:50]}"
