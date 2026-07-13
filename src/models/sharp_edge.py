"""
src/models/sharp_edge.py
「削ってはいけない角」を表現するPydanticモデル。
"""
from __future__ import annotations

import logging
from typing import List

from pydantic import BaseModel, Field, field_validator

from config.sharp_edge_vocabulary import SHARP_EDGE_TYPES

logger = logging.getLogger(__name__)


class SharpEdgeSpec(BaseModel):
    """
    品質向上工程で削ってはいけない角の仕様。

    preserve_on_quality_polish=True は品質磨き上げ時もこの角を保持することを意味する。
    False の場合は警告ログを出力し、品質監査での保全チェックを緩和する。
    """
    edge_type: str = Field(..., description="角の種類")
    description: str = Field(..., max_length=200, description="この角の内容（説明文）")
    key_phrase: str = Field(
        default="",
        max_length=20,
        description="本文から直接引用した20文字以内のキーフレーズ（品質化管理後も同一の字句が残ること）"
    )
    preserve_on_quality_polish: bool = Field(default=True, description="品質磨き上げ時に保持するか")

    @field_validator("edge_type")
    @classmethod
    def edge_type_must_be_known(cls, v: str) -> str:
        if v not in SHARP_EDGE_TYPES:
            raise ValueError(f"未知の角の種類です: {v}")
        return v

    @field_validator("key_phrase")
    @classmethod
    def key_phrase_must_be_brief(cls, v: str) -> str:
        if v and len(v) > 20:
            raise ValueError("key_phrase は20文字以内にしてください")
        return v

    @field_validator("preserve_on_quality_polish")
    @classmethod
    def warn_if_not_preserved(cls, v: bool) -> bool:
        if v is False:
            logger.warning("preserve_on_quality_polish=False: 品質磨き上げで角が削除される可能性があります")
        return v
