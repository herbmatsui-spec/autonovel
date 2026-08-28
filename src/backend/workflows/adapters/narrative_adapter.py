"""
src/backend/workflows/adapters/narrative_adapter.py - ナラティブ総合スコアアダプタ
"""

from __future__ import annotations

from typing import Any, Dict, Optional


async def update_narrative(
    hub: Any,
    ep: int,
    text: str,
    schema: Optional[Any] = None,
    service: Optional[Any] = None,
) -> Dict[str, Any]:
    """ナラティブ総合評価を実行し hub に反映する"""
    if service is not None:
        r = await service.score(text, schema)
    else:
        from src.services.narrative_scoring_service import NarrativeScoringService
        service_inst = NarrativeScoringService(llm=None, prompt_manager=None)
        r = await service_inst.score(text, schema)

    ep_int = int(ep)
    scores_dict = r if isinstance(r, dict) else dict(r)
    hub.narrative_scores[ep_int] = scores_dict
    hub.upsert_episode(ep_int, narrative=scores_dict)
    return scores_dict
