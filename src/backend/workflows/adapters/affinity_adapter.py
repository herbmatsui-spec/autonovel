"""
src/backend/workflows/adapters/affinity_adapter.py - 好感度トラッカーアダプタ
"""

from __future__ import annotations

from typing import Any, Optional


def update_affinity(
    hub: Any,
    ep: int,
    text: str,
    character_name: Optional[str] = None,
    tracker: Optional[Any] = None,
    character_names: Optional[list[str]] = None,
) -> None:
    """テキストを解析して好感度マップを更新し hub に記録する"""
    if tracker is not None:
        a = tracker
    else:
        from src.services.affinity_tracker import AffinityTracker
        a = AffinityTracker(initial_characters=character_names)

        # hub に既存の affinity_map / affinity_details があれば tracker に復元
        if hasattr(hub, "affinity_details") and hub.affinity_details:
            for cname, cdata in hub.affinity_details.items():
                if hasattr(cdata, "affinity_score"):
                    a.set_affinity(cdata)
        elif hasattr(hub, "affinity_map") and hub.affinity_map:
            for cname, cdata in hub.affinity_map.items():
                if hasattr(cdata, "affinity_score"):
                    a.set_affinity(cdata)
                elif isinstance(cdata, (int, float)):
                    from src.schemas.ux_schemas import AffinityData
                    a.set_affinity(AffinityData(character_name=cname, affinity_score=float(cdata)))

    res = a.update_from_text(text, character_name=character_name)

    # hub.affinity_map は {name: float} を格納（後方互換性）
    hub.affinity_map = {
        getattr(d, "character_name", getattr(d, "character", "")): getattr(
            d, "affinity_score", getattr(d, "score", 0.0)
        )
        for d in res
    }

    # hub.affinity_details にリッチな AffinityData を格納
    if not hasattr(hub, "affinity_details"):
        hub.affinity_details = {}
    for d in res:
        cname = getattr(d, "character_name", getattr(d, "character", ""))
        hub.affinity_details[cname] = d

    # 辞書シリアライズ形式で episode データに記録
    hub.upsert_episode(int(ep), affinity=dict(hub.affinity_map))
