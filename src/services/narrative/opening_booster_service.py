"""
opening_booster_service.py - 序盤1〜3話のクリフハンガー強制チェックおよびリライト指令生成サービス
"""
from __future__ import annotations

from typing import Any, List

from src.models.opening_booster import CliffhangerEvaluation, CliffhangerType
from src.services.auditors.cliffhanger_scorer import score_cliffhanger


class OpeningBoosterService:
    def __init__(self, target_eps: List[int] = [1, 2, 3]) -> None:
        self.target_eps = target_eps

    def evaluate_tail(self, ep_num: int, tail_text: str) -> CliffhangerEvaluation:
        if ep_num not in self.target_eps:
            return CliffhangerEvaluation(
                hook_type=CliffhangerType.TRIUMPH_TRIGGER,
                score=100.0,
                reason="対象外エピソードのため免除",
                tail_sentence=tail_text[-50:] if tail_text else "",
                requires_rewrite=False,
            )

        tail_stripped = tail_text.strip() if tail_text else ""
        if not tail_stripped:
            return CliffhangerEvaluation(
                hook_type=CliffhangerType.PEACEFUL,
                score=0.0,
                reason="本文が空です",
                tail_sentence="",
                requires_rewrite=True,
            )

        return score_cliffhanger(tail_stripped)

    def generate_rewrite_directive(self, evaluation: CliffhangerEvaluation) -> str:
        if not evaluation.requires_rewrite:
            return ""
        return (
            f"\n\n【🚨序盤クリフハンガー強制リライト指令】\n"
            f"現在の結末判定: {evaluation.hook_type.value} (スコア: {evaluation.score})\n"
            f"理由: {evaluation.reason}\n"
            f"指示: エピソード末尾を即座に「危機 (crisis)」「衝撃の真実 (shocking_truth)」「反撃の狼煙 (triumph_trigger)」のいずれかで締めくくってください。"
        )
