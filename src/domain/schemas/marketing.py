from __future__ import annotations
from typing import List
from pydantic import Field
from src.domain.schemas.base import AutoNovelBaseSchema


class CatchphraseItem(AutoNovelBaseSchema):
    """カクヨムキャッチコピー候補アイテム"""
    catchphrase: str = Field(..., description="キャッチコピー本文")
    score: float = Field(..., ge=0, le=100, description="CTRスコア（0-100）")
    char_count: int = Field(..., ge=0, description="文字数")
    type: str = Field(..., description="タイプ（dialogue, confession, reversal など）")


class CatchphraseResponse(AutoNovelBaseSchema):
    """キャッチコピー生成レスポンス"""
    catchphrases: List[CatchphraseItem] = Field(default_factory=list, description="キャッチコピー候補リスト")
    total_count: int = Field(default=0, description="総候補数")
    generated_at: str = Field(default_factory=lambda: __import__('datetime').datetime.utcnow().isoformat(), description="生成日時")