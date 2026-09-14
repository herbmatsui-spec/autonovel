"""
Character Flaw and Secret Motive Models.
PLAN 03: AI優等生病の外科的切除（生々しいエゴ・下品な打算・偏執的な毒気の注入）
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class SecretMotive(BaseModel):
    """キャラクターの裏の打算・俗物的な本音動機"""

    motive_type: str = Field(..., description="打算の種類 (金銭欲, 承認欲求, 独占欲, 復讐心, 見下し 等)")
    inner_monologue_sample: str = Field(..., description="心の中の生々しい・ゲスな呟きの例")
    physical_trigger: str = Field(..., description="感情が高ぶった際に出る身体的癖 (舌打ち, 爪を噛む, 目が濁る, 喉仏を動かす 等)")


class CharacterFlawProfile(BaseModel):
    """キャラクターの表向きの顔と隠されたエゴ・毒気プロファイル"""

    character_name: str = Field(..., description="対象キャラクター名")
    surface_persona: str = Field(..., description="表向きの善良な態度・建前")
    secret_flaw: SecretMotive = Field(..., description="裏の俗物的な動機")
    target_of_contempt: str = Field("", description="内心見下している・嘲笑している対象")
