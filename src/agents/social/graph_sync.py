"""Apache AGE Social Graph Synchronization (Step 51).

Saves journal entries, reactions/comments, and character dynamic relationships
into the Apache AGE graph database using Cypher queries.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from src.agents.social.models import (
    JournalEntry,
    SocialComment,
    RelationshipMetrics,
)

logger = logging.getLogger(__name__)


class SocialGraphSyncer:
    """Synchronizes social interactions (journals, comments, relationship metrics) with Apache AGE."""

    def __init__(self, age_client: Any = None, default_graph_name: str = "novel_graph") -> None:
        self.age_client = age_client
        self.default_graph_name = default_graph_name

    def sync_journals(
        self,
        session: Session | None,
        journals: list[JournalEntry],
        graph_name: str | None = None,
    ) -> int:
        """Upsert journal entries as graph nodes and link them to author characters.

        Creates:
        - Node: (journal_entry:journal_entry {name: entry_id, book_id, ep_num, theme, emotion, content})
        - Node: (Character {name: character_name})
        - Edge: (Character)-[:AUTHORED]->(journal_entry)
        """
        if not journals:
            return 0
        if not session or not self.age_client:
            logger.debug("Skipping AGE journal sync: session or age_client is not provided.")
            return 0

        gname = graph_name or self.default_graph_name
        synced_count = 0

        for j in journals:
            try:
                # 1. Upsert Character Node
                self.age_client.upsert_node(
                    session=session,
                    label="Character",
                    name=j.character_name,
                    properties={"character_id": j.character_id},
                    graph_name=gname,
                )

                # 2. Upsert journal_entry Node
                j_props = {
                    "entry_id": j.entry_id,
                    "book_id": j.book_id,
                    "ep_num": j.ep_num,
                    "scene_id": j.scene_id,
                    "character_id": j.character_id,
                    "character_name": j.character_name,
                    "theme": j.theme,
                    "emotion": j.emotion,
                    "content": j.content[:500],  # Bound length for property storage
                    "created_at": j.created_at.isoformat(),
                }
                self.age_client.upsert_node(
                    session=session,
                    label="journal_entry",
                    name=j.entry_id,
                    properties=j_props,
                    graph_name=gname,
                )

                # 3. Create AUTHORED Edge
                self.age_client.upsert_edge(
                    session=session,
                    source_label="Character",
                    source_name=j.character_name,
                    target_label="journal_entry",
                    target_name=j.entry_id,
                    relation_type="AUTHORED",
                    properties={"ep_num": j.ep_num, "entry_id": j.entry_id},
                    graph_name=gname,
                )
                synced_count += 1
            except Exception as e:
                logger.warning("Failed to sync journal %s to AGE: %s", j.entry_id, e)

        return synced_count

    def sync_comments(
        self,
        session: Session | None,
        comments: list[SocialComment],
        graph_name: str | None = None,
    ) -> int:
        """Upsert comments as graph edges onto journal entries and interaction between characters.

        Creates:
        - Node: (Character {name: from_character_name})
        - Edge: (Character)-[:COMMENT_ON]->(journal_entry)
        """
        if not comments:
            return 0
        if not session or not self.age_client:
            logger.debug("Skipping AGE comment sync: session or age_client is not provided.")
            return 0

        gname = graph_name or self.default_graph_name
        synced_count = 0

        for c in comments:
            try:
                # 1. Ensure commenting character node exists
                self.age_client.upsert_node(
                    session=session,
                    label="Character",
                    name=c.from_character_name,
                    properties={"character_id": c.from_character_id},
                    graph_name=gname,
                )

                # 2. Edge from commenting character to target journal entry
                edge_props = {
                    "comment_id": c.comment_id,
                    "reaction_type": c.reaction_type,
                    "trust_delta": c.trust_delta,
                    "tension_delta": c.tension_delta,
                    "content": c.content[:300],
                    "created_at": c.created_at.isoformat(),
                }
                self.age_client.upsert_edge(
                    session=session,
                    source_label="Character",
                    source_name=c.from_character_name,
                    target_label="journal_entry",
                    target_name=c.journal_id,
                    relation_type="COMMENT_ON",
                    properties=edge_props,
                    graph_name=gname,
                )
                synced_count += 1
            except Exception as e:
                logger.warning("Failed to sync comment %s to AGE: %s", c.comment_id, e)

        return synced_count

    def sync_relationship_metrics(
        self,
        session: Session | None,
        metrics: list[RelationshipMetrics],
        graph_name: str | None = None,
    ) -> int:
        """Upsert dynamic relationship metrics edge between character nodes.

        Creates:
        - Edge: (Character {name: char_a})-[:RELATIONSHIP]->(Character {name: char_b})
        """
        if not metrics:
            return 0
        if not session or not self.age_client:
            logger.debug("Skipping AGE metrics sync: session or age_client is not provided.")
            return 0

        gname = graph_name or self.default_graph_name
        synced_count = 0

        for m in metrics:
            try:
                # Ensure both characters exist
                self.age_client.upsert_node(
                    session=session,
                    label="Character",
                    name=m.char_a,
                    properties={},
                    graph_name=gname,
                )
                self.age_client.upsert_node(
                    session=session,
                    label="Character",
                    name=m.char_b,
                    properties={},
                    graph_name=gname,
                )

                rel_props = {
                    "trust_score": float(m.trust_score),
                    "tension_score": float(m.tension_score),
                    "affinity_score": float(m.affinity_score),
                    "last_interaction_ep": int(m.last_interaction_ep),
                }

                self.age_client.upsert_edge(
                    session=session,
                    source_label="Character",
                    source_name=m.char_a,
                    target_label="Character",
                    target_name=m.char_b,
                    relation_type="RELATIONSHIP",
                    properties=rel_props,
                    graph_name=gname,
                )
                synced_count += 1
            except Exception as e:
                logger.warning("Failed to sync relationship (%s, %s) to AGE: %s", m.char_a, m.char_b, e)

        return synced_count

    def sync_all(
        self,
        session: Session | None,
        journals: list[JournalEntry] | None = None,
        comments: list[SocialComment] | None = None,
        metrics: list[RelationshipMetrics] | None = None,
        graph_name: str | None = None,
    ) -> dict[str, Any]:
        """Convenience method to synchronize all social data elements into AGE."""
        j_cnt = self.sync_journals(session, journals or [], graph_name)
        c_cnt = self.sync_comments(session, comments or [], graph_name)
        m_cnt = self.sync_relationship_metrics(session, metrics or [], graph_name)

        return {
            "synced_journals": j_cnt,
            "synced_comments": c_cnt,
            "synced_metrics": m_cnt,
            "success": True,
        }


__all__ = ["SocialGraphSyncer"]
