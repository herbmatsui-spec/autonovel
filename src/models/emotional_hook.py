"""
src/models/emotional_hook.py
感情起点（刺さり）を表現するPydanticモデル。

品質は感情の従属変数であることを型で強制する。
"""
from __future__ import annotations

import logging
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from config.emotional_hook_vocabulary import validate_hook

logger = logging.getLogger(__name__)


class EmotionalHookSpec(BaseModel):
    """
    1話分の感情設計仕様。

    subordinate_to_quality=True は「品質はこの感情に従属する」ことを意味する。
    False の場合は警告ログを出力し、品質監査時に感情を殺さないチェックを緩和する。
    """
    hook_name: str = Field(..., description="感情起点名")
    one_line_intent: str = Field(..., max_length=120, description="1行で表した刺さり")
    target_tension_peak: int = Field(default=80, ge=0, le=100, description="目標tensionピーク値")
    subordinate_to_quality: bool = Field(default=True, description="品質はこの感情の従属変数")

    @field_validator("hook_name")
    @classmethod
    def hook_name_must_be_known(cls, v: str) -> str:
        if not validate_hook(v):
            raise ValueError(f"未知の感情起点名です: {v}")
        return v

    @field_validator("subordinate_to_quality")
    @classmethod
    def warn_if_quality_not_subordinate(cls, v: bool) -> bool:
        if v is False:
            logger.warning("subordinate_to_quality=False: 品質が感情に従属しなくなります")
        return v
