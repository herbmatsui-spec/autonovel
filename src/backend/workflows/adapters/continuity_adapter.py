"""
src/backend/workflows/adapters/continuity_adapter.py - 連続性トラッカーアダプタ
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional


def feed_continuity(
    hub: Any,
    scene_dict: Dict[str, Any],
    tracker: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """シーン情報を受け取り、連続性検証を実行して違反を hub に蓄積する"""
    if tracker is not None:
        active_tracker = tracker
    else:
        if getattr(hub, "tracker", None) is None:
            try:
                from novel_50ep.continuity_tracker import ContinuityTracker

                hub.tracker = ContinuityTracker()
            except ImportError:
                from src.agents.erotic.continuity import ContinuityTracker

                hub.tracker = ContinuityTracker()
        active_tracker = hub.tracker

    v: List[Dict[str, Any]] = []
    if hasattr(active_tracker, "feed"):
        v = active_tracker.feed(scene_dict) or []

    hub.continuity_violations.extend(v)
    ep = scene_dict.get("ep") or scene_dict.get("episode_num") or 1
    hub.upsert_episode(int(ep), continuity_violations=list(v))
    return v
