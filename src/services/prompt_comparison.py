"""
services/prompt_comparison.py - ジャンル別プロンプト A/B 比較

同一入力に対して複数のプロンプトバージョンで生成し、品質スコアで比較する。
既存の QualityScorer（score_all）で自動評価し、重み付けで勝者を決定する。
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_WEIGHTS = {
    "hook_retention": 0.2,
    "pacing": 0.15,
    "character_consistency": 0.15,
    "commercial_viability": 0.2,
    "emotional_resonance": 0.15,
    "coherence": 0.15,
}


async def score_output(text: str) -> Dict[str, float]:
    """QualityScorer を用いて出力を評価する。"""
    from src.services.quality_scorer import QualityScorer

    scorer = QualityScorer()
    try:
        return {
            "hook_retention": await scorer.score_hook_retention(text),
            "pacing": await scorer.score_pacing(text),
            "character_consistency": await scorer.score_character_consistency(text),
            "commercial_viability": await scorer.score_commercial_viability(text),
            "emotional_resonance": await scorer.score_emotional_resonance(text),
            "coherence": await scorer.score_coherence(text),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"scoring failed: {exc}")
        return {k: 0.0 for k in DEFAULT_WEIGHTS}


def weighted_total(scores: Dict[str, float], weights: Optional[Dict[str, float]] = None) -> float:
    """重み付け合計スコアを算出する。"""
    w = weights or DEFAULT_WEIGHTS
    total = 0.0
    for key, weight in w.items():
        total += scores.get(key, 0.0) * weight
    return round(total, 4)


def decide_winner(results: List[Dict[str, Any]], weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """各バージョンの評価結果から勝者を決定する。"""
    if not results:
        return {"winner_id": None, "reason": "no results"}
    best = max(results, key=lambda r: r["weighted_total"])
    return {"winner_id": best["version_id"], "winner_label": best["label"], "reason": "最高合計スコア"}


async def build_comparison(
    versions: List[Dict[str, Any]],
    texts: List[str],
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """バージョンごとの評価・勝者判定を行う。"""
    results: List[Dict[str, Any]] = []
    for ver, text in zip(versions, texts):
        scores = await score_output(text)
        results.append(
            {
                "version_id": ver.get("id"),
                "label": ver.get("version_tag", str(ver.get("id"))),
                "scores": scores,
                "weighted_total": weighted_total(scores, weights),
                "output_preview": (text or "")[:300],
            }
        )
    winner = decide_winner(results, weights)
    return {"weights": weights or DEFAULT_WEIGHTS, "results": results, "winner": winner}
