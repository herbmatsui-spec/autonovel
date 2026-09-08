import pytest
from unittest.mock import MagicMock
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.database.models.base_orm import Base
from src.backend.database.models import Book
from src.backend.database.social_repository import SocialRepository
from src.agents.social.manager import SocialInteractionManager
from src.agents.social.models import RelationshipMetrics, JournalEntry
from src.agents.context_builder_agent import ContextBuilderAgent


@pytest.fixture
async def async_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        book = Book(id=1, title="Test Novel")
        session.add(book)
        await session.commit()

    yield session_factory
    await engine.dispose()


def test_manager_prune_history():
    """Step 25の検証: インメモリ履歴の件数制限"""
    manager = SocialInteractionManager()
    manager._history_store = {
        ("Alice", "Bob"): [{"ep": i} for i in range(70)],
        ("Alice", "Charlie"): [{"ep": i} for i in range(20)],
    }
    pruned = manager.prune_history(max_entries_per_pair=50)
    assert pruned == 20
    assert len(manager._history_store[("Alice", "Bob")]) == 50
    assert len(manager._history_store[("Alice", "Charlie")]) == 20


@pytest.mark.asyncio
async def test_repository_cleanup_and_summaries(async_db):
    """Step 26, 28, 29, 30の検証: cleanup_old_history, summaries, context_builder"""
    session_factory = async_db
    async with session_factory() as session:
        repo = SocialRepository(session)

        # 1. 多数の履歴レコードを挿入
        for ep in range(1, 15):
            m = RelationshipMetrics(
                char_a="Hero",
                char_b="Rival",
                trust_score=50.0 + ep * 2,
                tension_score=50.0 - ep,
                affinity_score=50.0 + ep,
                last_interaction_ep=ep,
                dynamics_state="friends" if ep > 5 else "neutral",
            )
            await repo.record_history(book_id=1, char_a="Hero", char_b="Rival", episode_num=ep, metrics=m)

        # 日記レコードを複数話分挿入
        for ep in range(1, 5):
            j = JournalEntry(
                entry_id=f"j_{ep}",
                book_id=1,
                ep_num=ep,
                character_id="hero",
                character_name="Hero",
                content=f"第{ep}話の激戦を終えて、仲間の大切さを知った。",
                emotion="決意",
            )
            await repo.save_journal(book_id=1, character_name="Hero", episode_num=ep, journal=j)
        await session.commit()

        # Step 26: cleanup_old_history (最新5件のみ保持)
        deleted = await repo.cleanup_old_history(book_id=1, keep_latest_per_pair=5)
        assert deleted == 9  # 14件中、最新5件を残して9件削除
        hist = await repo.get_relationship_history(book_id=1, char_a="Hero", char_b="Rival", limit=10)
        assert len(hist) == 5

        # Step 28: get_important_journals_summary
        j_summary = await repo.get_important_journals_summary(book_id=1, current_ep=5, lookback=3)
        assert "直近エピソードの登場人物内面手記" in j_summary
        assert "第4話" in j_summary

        # Step 29: get_relationship_trends_summary
        t_summary = await repo.get_relationship_trends_summary(book_id=1)
        assert "動的心理関係性・トレンド" in t_summary
        assert "Hero ⇔ Rival" in t_summary

        # Step 30: ContextBuilderAgent への統合
        manager = SocialInteractionManager(social_repo=repo)
        cb_agent = ContextBuilderAgent(repo=None, llm=None, social_manager=manager)
        ctx = await cb_agent._get_social_dynamic_context(
            book_id=1,
            ep_num=5,
            social_manager=manager,
        )
        assert "登場人物内面手記" in ctx
        assert "動的心理関係性" in ctx


@pytest.mark.asyncio
async def test_active_char_filtering_and_bounds_and_fault_tolerance(async_db):
    """Step 31-34, 36の検証: active_charsフィルタリング, max_chars上限, 耐障害性"""
    session_factory = async_db
    async with session_factory() as session:
        repo = SocialRepository(session)

        # 2ペア関係性を挿入
        m1 = RelationshipMetrics(char_a="Hero", char_b="Rival", trust_score=80.0, tension_score=20.0, affinity_score=85.0)
        m2 = RelationshipMetrics(char_a="MobA", char_b="MobB", trust_score=50.0, tension_score=50.0, affinity_score=50.0)
        await repo.upsert_relationship(book_id=1, char_a="Hero", char_b="Rival", metrics=m1)
        await repo.upsert_relationship(book_id=1, char_a="MobA", char_b="MobB", metrics=m2)
        await session.commit()

        # Step 32: get_relationships_for_characters
        hero_rels = await repo.get_relationships_for_characters(book_id=1, char_names=["Hero"])
        assert len(hero_rels) == 1
        assert hero_rels[0]["char_a"] == "Hero" or hero_rels[0]["char_b"] == "Hero"

        # Step 31, 33: ContextBuilder で active_chars=["Hero"] の場合、Mobペアは含まれずHeroペアが含まれること
        manager = SocialInteractionManager(social_repo=repo)
        cb_agent = ContextBuilderAgent(repo=None, llm=None, social_manager=manager)
        ctx = await cb_agent._get_social_dynamic_context(
            book_id=1,
            ep_num=2,
            social_manager=manager,
            active_chars=[{"name": "Hero"}],
        )
        assert "Hero ⇔ Rival" in ctx
        assert "MobA ⇔ MobB" not in ctx

        # Step 34: max_chars 制限
        ctx_bounded = await cb_agent._get_social_dynamic_context(
            book_id=1,
            ep_num=2,
            social_manager=manager,
            active_chars=[{"name": "Hero"}],
            max_chars=40,
        )
        assert len(ctx_bounded) <= 40
        assert ctx_bounded.endswith("...")

        # Step 36: 例外発生時の完全耐障害フォールバック
        broken_manager = MagicMock()
        broken_manager.social_repo = MagicMock()
        broken_manager.social_repo.get_important_journals_summary.side_effect = RuntimeError("DB Crashed!")
        broken_manager.social_repo.get_relationship_trends_summary.side_effect = RuntimeError("DB Crashed!")
        broken_manager.get_all_relationships_for_character.side_effect = RuntimeError("Manager Crashed!")

        safe_ctx = await cb_agent._get_social_dynamic_context(
            book_id=1,
            ep_num=2,
            social_manager=broken_manager,
        )
        assert isinstance(safe_ctx, str)  # 例外を投げずに安全復旧すること


def test_novel_router_social_endpoints():
    """Step 35の検証: novel.py のソーシャルエンドポイント定義"""
    from src.backend.routers import novel
    routes = [r.path for r in novel.router.routes]
    assert any("social/relationships" in p for p in routes)
    assert any("social/journals" in p for p in routes)
    assert any("social/trends" in p for p in routes)
