from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class CharacterBase(BaseModel):
    """キャラクターの基底モデル"""
    character_id: int = Field(..., ge=1, description="キャラクターID")
    name: str = Field(..., min_length=1, max_length=100, description="名前")
    role: str = Field(..., max_length=50, description="役割 (protagonist/antagonist/supporting 等)")
    traits: List[str] = Field(default_factory=list, description="性格特性")
    background: Optional[str] = Field(default=None, max_length=2000, description="背景設定")
    relationships: Dict[str, str] = Field(default_factory=dict, description="他キャラとの関係")


class CharacterCreate(BaseModel):
    """キャラクター作成リクエスト"""
    name: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., max_length=50)
    traits: Optional[List[str]] = Field(default_factory=list)
    background: Optional[str] = Field(default=None, max_length=2000)
    relationships: Optional[Dict[str, str]] = Field(default_factory=dict)


class Character(CharacterBase):
    """キャラクターエンティティ — 完全なデータモデル"""
    current_emotion: Optional[str] = Field(default=None, max_length=100, description="現在の感情状態")
    tension_contribution: float = Field(default=0.0, ge=0.0, le=1.0, description="緊張への貢献度")
    emotional_resonance: float = Field(default=0.0, ge=0.0, le=1.0, description="感情的共鳴度")
    book_id: int = Field(default=0, ge=1, description="所属作品ID")

    model_config = ConfigDict(extra="forbid", from_attributes=True)
