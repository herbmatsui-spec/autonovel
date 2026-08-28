"""
src/backend/workflows/adapters/erotic_adapter.py - 官能品質アダプタ
"""

from __future__ import annotations

from typing import Any, Dict, Optional


def update_erotic(
    hub: Any,
    ep: int,
    text: str,
    scorer: Optional[Any] = None,
) -> Dict[str, Any]:
    """官能品質を評価し hub に反映する"""
    if scorer is not None:
        sc = scorer
    else:
        from src.agents.erotic.evaluator import EroticQualityScorer
        sc = EroticQualityScorer()

    rep = sc.score(text)

    # 属性または辞書からメトリクスを抽出
    if isinstance(rep, dict):
        rep_dict = rep
    elif hasattr(rep, "model_dump") and not hasattr(rep, "_mock_return_value"):
        try:
            rep_dict = rep.model_dump()
        except Exception:
            rep_dict = {}
    else:
        rep_dict = {}

    overall_score = getattr(rep, "overall_score", rep_dict.get("overall_score", 0.0))
    sensuality_score = getattr(rep, "sensuality_score", rep_dict.get("sensuality_score", 0.0))
    emotional_score = getattr(rep, "emotional_score", rep_dict.get("emotional_score", 0.0))
    psychological_score = getattr(rep, "psychological_score", rep_dict.get("psychological_score", 0.0))
    technical_score = getattr(rep, "technical_score", rep_dict.get("technical_score", 0.0))

    metrics = {
        "overall_score": float(overall_score) if overall_score is not None else 0.0,
        "sensuality_score": float(sensuality_score) if sensuality_score is not None else 0.0,
        "emotional_score": float(emotional_score) if emotional_score is not None else 0.0,
        "psychological_score": float(psychological_score) if psychological_score is not None else 0.0,
        "technical_score": float(technical_score) if technical_score is not None else 0.0,
        # 後方互換性エイリアス
        "score": float(overall_score) if overall_score is not None else 0.0,
        "intensity": float(sensuality_score) if sensuality_score is not None else 0.0,
        "coherence": float(technical_score) if technical_score is not None else 0.0,
    }

    ep_int = int(ep)
    hub.erotic_metrics[ep_int] = metrics
    hub.upsert_episode(ep_int, erotic=metrics)
    return metrics
