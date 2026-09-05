"""Dynamic Relationship Transition and Timeline Computation (Step 50)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.agents.social.models import JournalEntry, SocialComment, RelationshipMetrics
from src.agents.social.manager import SocialInteractionManager

logger = logging.getLogger(__name__)


class RelationshipHistoryRecord(BaseModel):
    """Historical snapshot of a relationship at a specific episode."""

    ep_num: int
    char_a: str
    char_b: str
    trust_score: float
    tension_score: float
    affinity_score: float
    trigger_summary: str = ""


class RelationshipDynamicsCalculator:
    """Calculates chronological trajectory of character relationships."""

    def __init__(self, initial_store: dict[tuple[str, str], RelationshipMetrics] | None = None) -> None:
        self.history: list[RelationshipHistoryRecord] = []
        self.metrics_store: dict[tuple[str, str], RelationshipMetrics] = dict(initial_store or {})

    def calculate_epoch_updates(
        self,
        author_name: str,
        comments: list[SocialComment],
        ep_num: int = 1,
    ) -> dict[tuple[str, str], RelationshipMetrics]:
        """Calculate relationship changes directly on local metrics_store."""
        for comment in comments:
            trust_d = comment.trust_delta
            tension_d = comment.tension_delta
            affinity_d = round((trust_d * 0.7) - (tension_d * 0.3), 1)

            pair = tuple(sorted([author_name.strip(), comment.from_character_name.strip()]))
            if pair not in self.metrics_store:
                self.metrics_store[pair] = RelationshipMetrics(
                    char_a=pair[0],
                    char_b=pair[1],
                    trust_score=50.0,
                    tension_score=50.0,
                    affinity_score=50.0,
                    last_interaction_ep=ep_num,
                )
            rel = self.metrics_store[pair]
            rel.trust_score = max(0.0, min(100.0, round(rel.trust_score + trust_d, 1)))
            rel.tension_score = max(0.0, min(100.0, round(rel.tension_score + tension_d, 1)))
            rel.affinity_score = max(0.0, min(100.0, round(rel.affinity_score + affinity_d, 1)))
            rel.last_interaction_ep = ep_num

            record = RelationshipHistoryRecord(
                ep_num=ep_num,
                char_a=rel.char_a,
                char_b=rel.char_b,
                trust_score=rel.trust_score,
                tension_score=rel.tension_score,
                affinity_score=rel.affinity_score,
                trigger_summary=f"Comment: {comment.reaction_type} ({comment.content[:30]}...)",
            )
            self.history.append(record)

        return self.metrics_store

    def apply_interaction_deltas(
        self,
        manager: SocialInteractionManager,
        journal: JournalEntry,
        comments: list[SocialComment],
        ep_num: int,
    ) -> list[RelationshipMetrics]:
        """Apply all trust, tension, and affinity deltas to manager and append history records."""
        updated_metrics = []
        author_name = journal.character_name

        for comment in comments:
            # 連動好感度: 信頼度の上昇で高まり、緊張度の上昇で下がる
            trust_d = comment.trust_delta

            tension_d = comment.tension_delta
            affinity_d = round((trust_d * 0.7) - (tension_d * 0.3), 1)

            rel = manager.update_relationship(
                char_a=author_name,
                char_b=comment.from_character_name,
                trust_delta=trust_d,
                tension_delta=tension_d,
                affinity_delta=affinity_d,
                ep_num=ep_num,
            )
            updated_metrics.append(rel)

            record = RelationshipHistoryRecord(
                ep_num=ep_num,
                char_a=rel.char_a,
                char_b=rel.char_b,
                trust_score=rel.trust_score,
                tension_score=rel.tension_score,
                affinity_score=rel.affinity_score,
                trigger_summary=f"Comment: {comment.reaction_type} ({comment.content[:30]}...)",
            )
            self.history.append(record)

        return updated_metrics

    def infer_relationship_trend(self, char_a: str, char_b: str) -> str:
        """Infer narrative relationship trend (e.g. deepening trust, growing hostility) from history."""
        pair_records = [
            r for r in self.history
            if (r.char_a == char_a and r.char_b == char_b) or (r.char_a == char_b and r.char_b == char_a)
        ]
        if len(pair_records) < 2:
            return "関係性形成期"

        first = pair_records[0]
        latest = pair_records[-1]

        trust_diff = latest.trust_score - first.trust_score
        tension_diff = latest.tension_score - first.tension_score

        if trust_diff >= 15.0 and tension_diff <= -10.0:
            return "信頼の急速な深化と結束"
        elif trust_diff <= -15.0 and tension_diff >= 15.0:
            return "深刻な疑念と対立の激化"
        elif tension_diff >= 20.0:
            return "一触即発の緊張状態"
        elif trust_diff >= 10.0:
            return "相互理解の進展"
        elif trust_diff <= -10.0:
            return "すれ違いによる距離感の拡大"
        return "安定的共存"


__all__ = [
    "RelationshipHistoryRecord",
    "RelationshipDynamicsCalculator",
]
