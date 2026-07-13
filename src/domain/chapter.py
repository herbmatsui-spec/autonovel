from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from src.domain.character import Character


class ChapterBase(BaseModel):
    """章の基底モデル"""
    ep_num: int = Field(..., ge=1, description="エピソード番号")
    title: str = Field(..., min_length=1, max_length=200, description="章タイトル")
    content: str = Field(default="", description="本文内容")
    status: str = Field(default="draft", pattern=r"^(draft|writing|completed|archived)$", description="ステータス")
    word_count: int = Field(default=0, ge=0, description="文字数")
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp(), description="作成日時")
    updated_at: float = Field(default_factory=lambda: datetime.now().timestamp(), description="更新日時")


class ChapterCreate(BaseModel):
    """章作成リクエスト"""
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(default="")
    ep_num: Optional[int] = Field(default=None, ge=1)


class Chapter(ChapterBase):
    """章エンティティ — 完全なデータモデル"""
    id: int = Field(..., ge=1, description="章ID")
    characters: List["Character"] = Field(default_factory=list, description="登場キャラクター")
    tension: float = Field(default=0.0, ge=0.0, le=1.0, description="緊張度")
    emotional_resonance: float = Field(default=0.0, ge=0.0, le=1.0, description="感情的共鳴度")
    plot_points: List[str] = Field(default_factory=list, description="プロットポイント")
    book_id: int = Field(default=0, ge=1, description="所属作品ID")

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    @property
    def is_completed(self) -> bool:
        """章が完了状態かどうか"""
        return self.status == "completed"
