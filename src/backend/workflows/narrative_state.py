"""
src/backend/workflows/narrative_state.py - NarrativeState 共通ハブ定義 (SSOT)

強化系機能（Tension, Affinity, Quality, Narrative, Erotic, Continuity, Foreshadow）
が読み書きする単一の共有状態ハブ。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class NarrativeState:
    """ナラティブ状態のSSOT（Single Source of Truth）ハブ"""

    book_id: int = 1
    branch_id: int = 1
    episodes: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    tension_curve: List[float] = field(default_factory=list)
    affinity_map: Dict[str, Any] = field(default_factory=dict)
    foreshadow_registry: List[Dict[str, Any]] = field(default_factory=list)
    continuity_violations: List[Dict[str, Any]] = field(default_factory=list)
    quality_scores: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    erotic_metrics: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    narrative_scores: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    tracker: Optional[Any] = field(default=None, repr=False)

    def to_dict(self) -> Dict[str, Any]:
        """ハブの状態をシリアライズ可能な辞書に変換する"""
        aff_dict = {}
        for k, v in self.affinity_map.items():
            if hasattr(v, "model_dump"):
                aff_dict[k] = v.model_dump()
            elif hasattr(v, "__dict__"):
                aff_dict[k] = dict(v.__dict__)
            else:
                aff_dict[k] = v

        return {
            "book_id": self.book_id,
            "branch_id": self.branch_id,
            "episodes": {int(k): v for k, v in self.episodes.items()},
            "tension_curve": list(self.tension_curve),
            "affinity_map": aff_dict,
            "foreshadow_registry": list(self.foreshadow_registry),
            "continuity_violations": list(self.continuity_violations),
            "quality_scores": {int(k): v for k, v in self.quality_scores.items()},
            "erotic_metrics": {int(k): v for k, v in self.erotic_metrics.items()},
            "narrative_scores": {int(k): v for k, v in self.narrative_scores.items()},
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> NarrativeState:
        """辞書から NarrativeState を復元する"""
        if not d:
            return cls()

        from src.schemas.ux_schemas import AffinityData

        episodes = {int(k): v for k, v in d.get("episodes", {}).items()}
        quality_scores = {int(k): v for k, v in d.get("quality_scores", {}).items()}
        erotic_metrics = {int(k): v for k, v in d.get("erotic_metrics", {}).items()}
        narrative_scores = {int(k): v for k, v in d.get("narrative_scores", {}).items()}

        raw_affinity = d.get("affinity_map", {})
        parsed_affinity: Dict[str, Any] = {}
        for k, v in raw_affinity.items():
            if isinstance(v, dict):
                try:
                    parsed_affinity[k] = AffinityData(**v)
                except Exception:
                    parsed_affinity[k] = v
            else:
                parsed_affinity[k] = v

        return cls(
            book_id=d.get("book_id", 1),
            branch_id=d.get("branch_id", 1),
            episodes=episodes,
            tension_curve=list(d.get("tension_curve", [])),
            affinity_map=parsed_affinity,
            foreshadow_registry=list(d.get("foreshadow_registry", [])),
            continuity_violations=list(d.get("continuity_violations", [])),
            quality_scores=quality_scores,
            erotic_metrics=erotic_metrics,
            narrative_scores=narrative_scores,
        )

    def upsert_episode(self, ep: int, **fields: Any) -> None:
        """話単位のデータを安全に更新する"""
        ep_int = int(ep)
        self.episodes.setdefault(ep_int, {}).update(fields)
