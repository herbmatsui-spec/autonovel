from __future__ import annotations
import logging
from typing import Any
from src.services.auditors.rule_based_metrics import (
    calculate_sentence_rhythm,
    calculate_dialogue_ratio,
    calculate_kanji_ratio,
    detect_ai_cliches,
    evaluate_cliffhanger_ending,
)
from src.models.unified_audit import UnifiedAuditReport, QualitativeAudit

logger = logging.getLogger(__name__)

class UnifiedAuditor:
    def __init__(self, llm_gateway: Any = None):
        self.llm = llm_gateway

    def audit_quantitative(self, text: str) -> tuple[float, dict[str, Any]]:
        """静的ルールベースの定量的スコア（0ms, 0コスト）を算出"""
        rhythm = calculate_sentence_rhythm(text)
        dialogue = calculate_dialogue_ratio(text)
        cliches = detect_ai_cliches(text)
        cliff = evaluate_cliffhanger_ending(text)

        # 静的スコアの加重平均
        score = (rhythm.score * 0.3) + (dialogue.score * 0.3) + (cliff * 0.4)
        if cliches:
            score = max(0.0, score - len(cliches) * 5.0)

        meta = {
            "rhythm_score": rhythm.score,
            "dialogue_ratio": dialogue.ratio,
            "cliches": cliches,
            "cliffhanger_score": cliff,
        }
        return score, meta
