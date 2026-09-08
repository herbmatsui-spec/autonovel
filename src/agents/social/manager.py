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
        social_repo: Any = None,
    ) -> None:
        self.llm = llm_adapter
        self.age_client = age_client
        self.repo = repo
        # SocialRepository が渡されているか、repo が SocialRepository 互換の場合に保持
        self.social_repo = social_repo or (
            repo if repo is not None and hasattr(repo, "upsert_relationship") else None
        )
        # (char_a, char_b) -> RelationshipMetrics (インメモリキャッシュ)
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

    async def get_relationship_async(
        self,
        char_a: str,
        char_b: str,
        book_id: int = 1,
    ) -> RelationshipMetrics:
        """非同期で関係性メトリクスを取得（DBに存在すればロードしてメモリキャッシュを同期）(Step 14)"""
        pair = self._normalize_pair(char_a, char_b)
        if self.social_repo is not None:
            rel = await self.social_repo.get_relationship(book_id, pair[0], pair[1])
            if rel is not None:
                self._relationship_store[pair] = rel
                return rel

        return self.get_relationship(char_a, char_b)

    @staticmethod
    def compute_dynamics_state(affinity: float, trust: float, tension: float) -> str:
        """Dynamically compute state tag from scores (Step 21)."""
        if trust >= 70.0 and affinity >= 70.0:
            return "allies"
        elif tension >= 70.0 and trust <= 30.0:
            return "hostile"
        elif tension >= 60.0 and affinity >= 50.0:
            return "rivals"
        elif tension >= 50.0:
            return "tense"
        elif affinity >= 60.0 or trust >= 60.0:
            return "friendly"
        return "neutral"

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
        rel.dynamics_state = self.compute_dynamics_state(rel.affinity_score, rel.trust_score, rel.tension_score)
        rel.last_interaction_ep = ep_num
        return rel

    async def update_relationship_async(
        self,
        char_a: str,
        char_b: str,
        trust_delta: float = 0.0,
        tension_delta: float = 0.0,
        affinity_delta: float = 0.0,
        ep_num: int = 1,
        book_id: int = 1,
        trigger_event: str = "",
    ) -> RelationshipMetrics:
        """非同期で関係性を更新し、DBへupsertおよび履歴スナップショットを記録 (Step 15)"""
        # DBに既存データがあればロード
        await self.get_relationship_async(char_a, char_b, book_id=book_id)
        rel = self.update_relationship(
            char_a, char_b, trust_delta, tension_delta, affinity_delta, ep_num
        )

        if self.social_repo is not None:
            pair = self._normalize_pair(char_a, char_b)
            await self.social_repo.upsert_relationship(book_id, pair[0], pair[1], rel)
            await self.social_repo.record_history(
                book_id, pair[0], pair[1], ep_num, rel, trigger_event=trigger_event
            )

        return rel

    def get_all_relationships(self) -> dict[tuple[str, str], RelationshipMetrics]:
        """インメモリに保持されている全関係性を取得する (Step 16)"""
        return dict(self._relationship_store)

    async def get_all_relationships_async(
        self, book_id: int = 1
    ) -> dict[tuple[str, str], RelationshipMetrics]:
        """DBから全関係性をロードしてキャッシュを更新し、返す (Step 16)"""
        if self.social_repo is not None:
            rels = await self.social_repo.get_all_relationships(book_id)
            self._relationship_store.update(rels)
        return self.get_all_relationships()

    def get_all_relationships_for_character(self, character_name: str) -> list[RelationshipMetrics]:
        """Retrieve all tracked relationships involving the given character."""
        name = character_name.strip()
        return [
            rel for rel in self._relationship_store.values()
            if rel.char_a == name or rel.char_b == name
        ]

    def prune_history(self, max_entries_per_pair: int = 50) -> int:
        """インメモリの関係性履歴をキャラクターペアごとに最大件数に制限（メモリ肥大化防止）(Step 25)"""
        pruned_count = 0
        if not hasattr(self, "_history_store"):
            self._history_store = {}
            return 0

        for pair, history_list in list(self._history_store.items()):
            if len(history_list) > max_entries_per_pair:
                excess = len(history_list) - max_entries_per_pair
                self._history_store[pair] = history_list[-max_entries_per_pair:]
                pruned_count += excess

        return pruned_count

    async def process_scene_async(
        self,
        book_id: int,
        ep_num: int,
        scene_text: str = "",
        characters: list[dict[str, Any]] | None = None,
        session: Any = None,
        graph_name: str | None = None,
    ) -> dict[str, Any]:
        """Process scene events asynchronously: parallel journals & reactions, DB persistence, AGE sync (Step 19)."""
        import asyncio
        from src.agents.social.journals import generate_scene_journals_async
        from src.agents.social.comments import simulate_character_reactions_async
        from src.agents.social.dynamics import RelationshipDynamicsCalculator
        from src.agents.social.graph_sync import SocialGraphSyncer

        chars = characters or [
            {"id": "hero", "name": "主人公", "role": "主人公"},
            {"id": "rival", "name": "ライバル", "role": "好敵手"},
        ]

        logger.info(
            "Processing social scene async for book_id=%s, ep_num=%s with %d characters",
            book_id,
            ep_num,
            len(chars),
        )

        # 1. Generate journals in parallel
        journals: list[JournalEntry] = await generate_scene_journals_async(
            scene_text=scene_text,
            characters=chars,
            book_id=book_id,
            ep_num=ep_num,
            llm=self.llm,
        )

        # 2. Simulate comments / reactions in parallel for each journal
        comment_tasks = [
            simulate_character_reactions_async(
                journal=j,
                other_characters=chars,
                llm=self.llm,
            )
            for j in journals
        ]
        comment_results = await asyncio.gather(*comment_tasks, return_exceptions=True)

        all_comments: list[SocialComment] = []
        for res in comment_results:
            if isinstance(res, list):
                all_comments.extend(res)
            else:
                logger.error("Error simulating reactions for journal: %s", res)

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

        # 4. DB永続化 (SocialRepository が設定されている場合)
        if self.social_repo is not None:
            try:
                # 日記の保存
                for j in journals:
                    await self.social_repo.save_journal(
                        book_id=book_id,
                        character_name=j.character_name,
                        episode_num=ep_num,
                        journal=j,
                    )
                # コメントの保存
                for c in all_comments:
                    await self.social_repo.save_comment(
                        book_id=book_id,
                        character_name=c.from_character_name,
                        episode_num=ep_num,
                        comment=c,
                    )
                # 関係性および履歴の保存
                for (c_a, c_b), metrics in self._relationship_store.items():
                    if c_a <= c_b:  # ペアごとに一度だけ記録
                        await self.social_repo.upsert_relationship(book_id, c_a, c_b, metrics)
                        await self.social_repo.record_history(
                            book_id=book_id,
                            char_a=c_a,
                            char_b=c_b,
                            episode_num=ep_num,
                            metrics=metrics,
                            trigger_event=f"Episode {ep_num} scene",
                        )
            except Exception as e:
                logger.error("Failed to persist social scene data to DB: %s", e)

        # 5. Sync to Apache AGE
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

    def process_scene(
        self,
        book_id: int,
        ep_num: int,
        scene_text: str = "",
        characters: list[dict[str, Any]] | None = None,
        session: Any = None,
        graph_name: str | None = None,
    ) -> dict[str, Any]:
        """Process scene events synchronously (Step 20 - backwards compatible wrapper)."""
        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run,
                    self.process_scene_async(
                        book_id=book_id,
                        ep_num=ep_num,
                        scene_text=scene_text,
                        characters=characters,
                        session=session,
                        graph_name=graph_name,
                    ),
                )
                return future.result()
        else:
            return asyncio.run(
                self.process_scene_async(
                    book_id=book_id,
                    ep_num=ep_num,
                    scene_text=scene_text,
                    characters=characters,
                    session=session,
                    graph_name=graph_name,
                )
            )


__all__ = ["SocialInteractionManager"]

