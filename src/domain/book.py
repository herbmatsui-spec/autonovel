from datetime import datetime
from typing import TYPE_CHECKING, List

from pydantic import BaseModel, ConfigDict, Field, field_validator

if TYPE_CHECKING:
    from src.domain.chapter import Chapter


class BookBase(BaseModel):
    """作品の基底モデル — 新規作成・更新時に使用"""
    title: str = Field(..., min_length=1, max_length=200, description="作品タイトル")
    author: str = Field(default="", max_length=100, description="作者名")
    genre: str = Field(default="", max_length=50, description="ジャンル")
    status: str = Field(default="draft", pattern=r"^(draft|active|completed|archived)$", description="ステータス")
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp(), description="作成日時")
    updated_at: float = Field(default_factory=lambda: datetime.now().timestamp(), description="更新日時")


class BookCreate(BaseModel):
    """作品作成リクエスト"""
    title: str = Field(..., min_length=1, max_length=200)
    author: str = Field(default="", max_length=100)
    genre: str = Field(default="", max_length=50)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("タイトルは空白のみでは設定できません")
        return v.strip()


class Book(BookBase):
    """作品エンティティ — 完全なデータモデル"""
    id: int = Field(..., ge=1, description="作品ID")
    chapters: List["Chapter"] = Field(default_factory=list, description="章一覧")
    tension: float = Field(default=0.0, ge=0.0, le=1.0, description="緊張度 (0-1)")
    emotional_resonance: float = Field(default=0.0, ge=0.0, le=1.0, description="感情的共鳴度 (0-1)")
    cumulative_stress: float = Field(default=0.0, description="累積ストレス値")

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    @property
    def is_completed(self) -> bool:
        """作品が完了状態かどうか"""
        return self.status == "completed"

    @property
    def chapter_count(self) -> int:
        """章の数"""
        return len(self.chapters)
