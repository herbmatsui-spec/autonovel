"""
src/backend/workflows/adapters/quality_adapter.py - 品質スコアアダプタ
"""

from __future__ import annotations

from typing import Any, Dict, Optional


async def update_quality(
    hub: Any,
    ep: int,
    text: str,
    scorer: Optional[Any] = None,
) -> Dict[str, Any]:
    """文章の品質スコアを計測し hub に格納する"""
    if scorer is not None:
        sc = scorer
    else:
        from src.services.quality_scorer import QualityScorer
        sc = QualityScorer()

    r = await sc.score_all(text)
    if hasattr(r, "model_dump"):
        scores_dict = r.model_dump()
    elif hasattr(r, "__dict__"):
        scores_dict = r.__dict__
    else:
        scores_dict = dict(r)

    ep_int = int(ep)
    hub.quality_scores[ep_int] = scores_dict
    hub.upsert_episode(ep_int, quality=scores_dict)
    return scores_dict
