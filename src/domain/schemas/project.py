from __future__ import annotations
from typing import Optional, List
from pydantic import Field
from src.domain.schemas.base import TimestampedSchema, AutoNovelBaseSchema

class BookSchema(TimestampedSchema):
    id: int
    project_id: int
    title: str = Field(..., max_length=200)
    genre: str = Field(default="fantasy")
    synopsis: str = Field(default="")
    total_words: int = 0
    target_chapters: int = 20

    # 覇権プロットアイデア出しパラメータ（v4より完全継承）
    cheat_scale: int = Field(default=4, ge=1, le=5, description="チート度（1:微チート〜5:理不尽無双）")
    growth_curve: str = Field(default="最初からカンスト(無双)", description="成長曲線モデル")
    system_assist: int = Field(default=70, ge=0, le=100, description="ステータス・システム関与度%")
    cost_severity: int = Field(default=2, ge=1, le=5, description="能力の代償・世界のリスク過酷度")
    thematic_core: str = Field(default="", description="物語の根底にあるテーマ・哲学的問い")

class ProjectSchema(TimestampedSchema):
    id: int
    name: str = Field(..., max_length=100)
    description: str = Field(default="")
    books: List[BookSchema] = Field(default_factory=list)

class ProjectCreateRequest(AutoNovelBaseSchema):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(default="")
    genre: str = Field(default="fantasy")
    target_chapters: int = 20
    cheat_scale: int = Field(default=4, ge=1, le=5)
    growth_curve: str = Field(default="最初からカンスト(無双)")
    system_assist: int = Field(default=70, ge=0, le=100)
    cost_severity: int = Field(default=2, ge=1, le=5)
    thematic_core: str = Field(default="")
