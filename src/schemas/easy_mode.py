"""src/schemas/easy_mode.py - かんたんモード入出力スキーマ。

src.domain.entities.easy_mode の全エンティティを再エクスポートし、
Studioモード受入やAPIルーティングでのスキーマ整合を保証する。
"""

from __future__ import annotations

from src.domain.entities.easy_mode import (
    CharacterParams,
    DigestRequest,
    DigestResponse,
    DigestStatus,
    EasyModeInput,
    ExportRequestPayload,
    FullAutoRequest,
    GachaPlan,
    GachaPlanType,
    GachaRequest,
    GachaResponse,
    GenerationResponse,
    LLMConfigOverride,
    PromotionRequest,
    PromotionResponse,
    ReversePlotGeneratePayload,
    StreamQueryInput,
)

# 互換エイリアス
WizardInput = EasyModeInput
WizardGenerationResponse = GenerationResponse

__all__ = [
    "CharacterParams",
    "LLMConfigOverride",
    "EasyModeInput",
    "StreamQueryInput",
    "GenerationResponse",
    "GachaPlanType",
    "DigestStatus",
    "GachaPlan",
    "GachaRequest",
    "GachaResponse",
    "DigestRequest",
    "DigestResponse",
    "PromotionRequest",
    "PromotionResponse",
    "ReversePlotGeneratePayload",
    "ExportRequestPayload",
    "FullAutoRequest",
    "WizardInput",
    "WizardGenerationResponse",
]
