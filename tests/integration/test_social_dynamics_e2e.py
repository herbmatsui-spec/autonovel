"""E2E Integration Test for Character Social Dynamics (Step 65)."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.social.manager import SocialInteractionManager
from src.agents.social.models import RelationshipMetrics
from src.backend.database.models import Book, Base
from src.backend.database.social_repository import SocialRepository
from src.core.container import AppContainer


@pytest.mark.asyncio
async def test_social_dynamics_lifecycle_e2e():
    """Verify full lifecycle: relationship creation -> scene update -> history tracking -> prune."""
    db = AppContainer.db()
    
    # Ensure tables exist
    async_eng = getattr(db, "engine", None)
    if async_eng is not None and hasattr(async_eng, "begin"):
        async with async_eng.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    book_id = 8888
    async with db.get_session() as session:
        from sqlalchemy import select
        res = await session.execute(select(Book).where(Book.id == book_id))
        if not res.scalar_one_or_none():
            session.add(Book(id=book_id, title="E2E Novel", genre="fantasy"))
            await session.commit()

    repo = SocialRepository(db)
    mock_llm = AsyncMock()
    mock_llm.generate = AsyncMock(return_value="Simulation output text")

    manager = SocialInteractionManager(llm_adapter=mock_llm, social_repo=repo)

    try:
        # 1. Update relationship via manager
        rel = await manager.update_relationship_async(
            char_a="Alice",
            char_b="Bob",
            trust_delta=30.0,
            tension_delta=-35.0,
            affinity_delta=25.0,
            ep_num=1,
            book_id=book_id,
            trigger_event="First alliance formed",
        )
        assert rel.trust_score == 80.0
        assert rel.dynamics_state == "allies"

        # 2. Verify stored in DB and reloadable via manager
        loaded_rel = await manager.get_relationship_async("Alice", "Bob", book_id=book_id)
        assert loaded_rel is not None
        assert loaded_rel.trust_score == 80.0
        assert loaded_rel.dynamics_state == "allies"

        # 3. Simulate multiple episode progression
        for ep in range(2, 6):
            updated_m = RelationshipMetrics(
                char_a="Alice",
                char_b="Bob",
                affinity_score=75.0 + ep,
                trust_score=80.0 - ep,
                tension_score=15.0 + (ep * 5),
                dynamics_state="developing",
                last_interaction_ep=ep,
            )
            await repo.record_history(
                book_id=book_id,
                char_a="Alice",
                char_b="Bob",
                episode_num=ep,
                metrics=updated_m,
                trigger_event=f"Dispute in episode {ep}",
            )

        # 4. Check history retrieval (1 from update_relationship_async + 4 from loop = 5 total)
        histories = await repo.get_relationship_history(book_id, "Alice", "Bob", limit=10)
        assert len(histories) == 5
        assert histories[-1]["episode_num"] == 5

        # 5. Summaries generation for ContextBuilder
        summary_trends = await repo.get_relationship_trends_summary(book_id)
        assert "Alice" in summary_trends and "Bob" in summary_trends

        # 6. History pruning (5 - 2 = 3 deleted)
        deleted = await repo.cleanup_old_history(book_id=book_id, keep_latest_per_pair=2)
        assert deleted == 3

        remaining = await repo.get_relationship_history(book_id, "Alice", "Bob", limit=10)
        assert len(remaining) == 2

    finally:
        async with db.get_session() as session:
            from sqlalchemy import delete
            from src.backend.database.models import CharacterRelationship
            await session.execute(delete(CharacterRelationship).where(CharacterRelationship.book_id == book_id))
            await session.execute(delete(Book).where(Book.id == book_id))
            await session.commit()
