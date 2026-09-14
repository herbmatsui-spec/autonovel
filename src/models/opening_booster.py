"""
Pydantic models for Opening Booster and Cliffhanger Scorer.
PLAN 02: 序盤3話特化型 ドーパミン注入・クリフハンガー強制エンジン
"""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class CliffhangerType(str, Enum):
    CRISIS = "crisis"                     # 命や立場の危機直前で終了
    SHOCKING_TRUTH = "shocking_truth"     # 衝撃の事実判明・裏切りで終了
    TRIUMPH_TRIGGER = "triumph_trigger"   # これから反撃という瞬間で終了
    PEACEFUL = "peaceful"                 # 平穏（不合格・リライト対象）


class CliffhangerEvaluation(BaseModel):
    hook_type: CliffhangerType
    score: float = Field(..., ge=0.0, le=100.0)
    reason: str
    tail_sentence: str
    requires_rewrite: bool


class OpeningEpisodeConfig(BaseModel):
    ep_num: int = Field(..., ge=1, le=3)
    target_word_count: int = Field(2500, ge=1500, le=4000)
    inciting_incident: str
    payoff_moment: str
