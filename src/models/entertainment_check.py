"""
src/models/entertainment_check.py
早期面白さ検証の結果を表現するPydanticモデル。

品質を評価せず、面白さのみを検証する。
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class EntertainmentCheckResult(BaseModel):
    """
    ラフプロット・冒頭500字に対する面白さ検証結果。
    """
    interest_score: int = Field(..., ge=0, le=100, description="興味を引く度 (0-100)")
    physiological_reaction: str = Field(..., description="読者の生理反応: 涙/怒り/背筋/共感/無反応 等")
    would_continue_reading: bool = Field(..., description="読み進めたいか")
    feedback: str = Field(..., max_length=300, description="面白さに関するフィードバック")
