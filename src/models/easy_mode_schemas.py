"""かんたんモード用 Pydantic スキーマ定義。"""
from __future__ import annotations

from pydantic import BaseModel, Field


class CharacterParams(BaseModel):
    """キャラクター設定パラメータ。"""

    name: str = Field(default="", max_length=100)
    personality: str = Field(default="", max_length=500)
    ability: str = Field(default="", max_length=500)
    genre: str = Field(default="", max_length=100)


class EasyModeInput(BaseModel):
    """かんたんモード生成リクエスト入力。"""

    chapter_history: list[str] = Field(default_factory=list)
    current_chapter: str = ""
    character_params: CharacterParams = Field(default_factory=CharacterParams)
    content_length_limit: int = Field(default=2000, ge=1, le=10000)


class GenerationResponse(BaseModel):
    """かんたんモード生成レスポンス。"""

    task_id: str | None = None
    output: str = ""
    completion_time_ms: int = 0
    error: str = ""
    suggestions: list[str] = Field(default_factory=list)


__all__ = ["CharacterParams", "EasyModeInput", "GenerationResponse"]
