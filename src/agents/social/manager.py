"""SocialInteractionManager Orchestrator Base (Step 46)."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from src.agents.social.models import (
    JournalEntry,
    SocialComment,
    RelationshipMetrics,
)

logger = logging.getLogger(__name__)


class SocialInteractionManager:
    """Orchestrates character social discovery, journals, reactions, and dynamic relationship tracking."""

    def __init__(
        self,
        llm_adapter: Any = None,
        age_client: Any = None,
        repo: Any = None,
    ) -> None:
        self.llm = llm_adapter
        self.age_client = age_client
        self.repo = repo
        # (char_a, char_b) -> RelationshipMetrics
        self._relationship_store: dict[tuple[str, str], RelationshipMetrics] = {}

    def _normalize_pair(self, char_a: str, char_b: str) -> tuple[str, str]:
        """Normalize character pair key symmetrically."""
        return tuple(sorted([char_a.strip(), char_b.strip()]))

    def get_relationship(self, char_a: str, char_b: str) -> RelationshipMetrics:
        """Get current relationship metrics between two characters (default 50/50/50)."""
        pair = self._normalize_pair(char_a, char_b)
        if pair not in self._relationship_store:
            self._relationship_store[pair] = RelationshipMetrics(
                char_a=pair[0],
                char_b=pair[1],
                trust_score=50.0,
                tension_score=50.0,
                affinity_score=50.0,
            )
        return self._relationship_store[pair]

    def update_relationship(
        self,
        char_a: str,
        char_b: str,
        trust_delta: float = 0.0,
        tension_delta: float = 0.0,
        affinity_delta: float = 0.0,
        ep_num: int = 1,
    ) -> RelationshipMetrics:
        """Update relationship scores with clipping between 0.0 and 100.0."""
        rel = self.get_relationship(char_a, char_b)
        rel.trust_score = max(0.0, min(100.0, round(rel.trust_score + trust_delta, 1)))
        rel.tension_score = max(0.0, min(100.0, round(rel.tension_score + tension_delta, 1)))
        rel.affinity_score = max(0.0, min(100.0, round(rel.affinity_score + affinity_delta, 1)))
        rel.last_interaction_ep = ep_num
        return rel

    def get_all_relationships_for_character(self, character_name: str) -> list[RelationshipMetrics]:
        """Retrieve all tracked relationships involving the given character."""
        name = character_name.strip()
        return [
            rel for rel in self._relationship_store.values()
            if rel.char_a == name or rel.char_b == name
        ]

    def process_scene(
        self,
        book_id: int,
        ep_num: int,
        scene_text: str = "",
        characters: list[dict[str, Any]] | None = None,
        session: Any = None,
        graph_name: str | None = None,
    ) -> dict[str, Any]:
        """Process scene events: generate journals, simulate reactions, update metrics, sync to AGE."""
        from src.agents.social.journals import generate_scene_journals
        from src.agents.social.comments import simulate_character_reactions
        from src.agents.social.dynamics import RelationshipDynamicsCalculator
        from src.agents.social.graph_sync import SocialGraphSyncer

        chars = characters or [
            {"id": "hero", "name": "主人公", "role": "主人公"},
            {"id": "rival", "name": "ライバル", "role": "好敵手"},
        ]

        logger.info("Processing social scene for book_id=%s, ep_num=%s with %d characters", book_id, ep_num, len(chars))

        # 1. Generate journals
        journals: list[JournalEntry] = generate_scene_journals(
            scene_text=scene_text,
            characters=chars,
            book_id=book_id,
            ep_num=ep_num,
            llm=self.llm,
        )

        # 2. Simulate comments / reactions
        all_comments: list[SocialComment] = []
        for j in journals:
            comments = simulate_character_reactions(
                journal=j,
                other_characters=chars,
                llm=self.llm,
            )
            all_comments.extend(comments)

        # 3. Calculate relationship dynamics
        calc = RelationshipDynamicsCalculator(initial_store=self._relationship_store)
        for j in journals:
            j_comments = [c for c in all_comments if c.journal_id == j.entry_id]
            if j_comments:
                calc.calculate_epoch_updates(
                    author_name=j.character_name,
                    comments=j_comments,
                    ep_num=ep_num,
                )
        self._relationship_store = calc.metrics_store

        # 4. Sync to Apache AGE
        syncer = SocialGraphSyncer(age_client=self.age_client, default_graph_name=graph_name or "novel_graph")
        sync_res = syncer.sync_all(
            session=session,
            journals=journals,
            comments=all_comments,
            metrics=list(self._relationship_store.values()),
            graph_name=graph_name,
        )

        return {
            "journals": journals,
            "comments": all_comments,
            "metrics": list(self._relationship_store.values()),
            "sync_result": sync_res,
            "success": True,
        }


__all__ = ["SocialInteractionManager"]

