import pytest
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.database.models.base_orm import Base
from src.backend.database.models import Book
from src.backend.database.social_repository import SocialRepository
from src.agents.social.manager import SocialInteractionManager
from src.agents.social.journals import generate_multi_perspective_journals_async
from src.agents.social.comments import simulate_character_reactions_async
from src.agents.social.models import JournalEntry


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


@pytest.mark.asyncio
async def test_manager_social_repo_integration(async_db):
    """Step 13-16の検証: SocialInteractionManagerとSocialRepositoryの連携"""
    session_factory = async_db
    async with session_factory() as session:
        repo = SocialRepository(session)
        manager = SocialInteractionManager(social_repo=repo)

        # 1. get_relationship_async（初期値）
        rel = await manager.get_relationship_async("Hero", "Rival", book_id=1)
        assert rel.trust_score == 50.0
        assert rel.affinity_score == 50.0

        # 2. update_relationship_async（更新 & DB永続化 & 履歴記録）
        rel_up = await manager.update_relationship_async(
            char_a="Hero",
            char_b="Rival",
            trust_delta=20.0,
            tension_delta=-10.0,
            affinity_delta=15.0,
            ep_num=1,
            book_id=1,
            trigger_event="Co-op boss battle",
        )
        await session.commit()

        assert rel_up.trust_score == 70.0
        assert rel_up.tension_score == 40.0
        assert rel_up.affinity_score == 65.0

        # 3. 別のマネージャーインスタンスを作成し、DBから復元できるか確認
        manager2 = SocialInteractionManager(social_repo=repo)
        rel_loaded = await manager2.get_relationship_async("Hero", "Rival", book_id=1)
        assert rel_loaded.trust_score == 70.0
        assert rel_loaded.affinity_score == 65.0

        # 4. 履歴が記録されているか確認
        history = await repo.get_relationship_history(book_id=1, char_a="Hero", char_b="Rival")
        assert len(history) == 1
        assert history[0]["trust"] == 70.0
        assert history[0]["trigger_event"] == "Co-op boss battle"

        # 5. get_all_relationships_async
        all_rels = await manager2.get_all_relationships_async(book_id=1)
        assert ("Hero", "Rival") in all_rels or ("Rival", "Hero") in all_rels


@pytest.mark.asyncio
async def test_journals_and_comments_async():
    """Step 17-18の検証: 非同期並行での日記・リアクション生成"""
    chars = [
        {"id": "c1", "name": "勇者", "role": "主人公", "personality": "熱血"},
        {"id": "c2", "name": "魔王", "role": "敵", "personality": "冷酷"},
        {"id": "c3", "name": "賢者", "role": "師匠", "personality": "温厚"},
    ]

    # 非同期モックLLM
    mock_llm = MagicMock()
    mock_llm.generate.return_value = "これはテスト用の内面独白テキストです。"

    # 1. 非同期日記並行生成
    journals = await generate_multi_perspective_journals_async(
        scene_summary="決戦の地での対峙",
        characters=chars,
        book_id=1,
        ep_num=1,
        llm=mock_llm,
    )
    assert len(journals) == 3
    names = {j.character_name for j in journals}
    assert names == {"勇者", "魔王", "賢者"}

    # 2. 非同期コメント並行シミュレーション
    hero_journal = next(j for j in journals if j.character_name == "勇者")
    mock_llm.generate.return_value = "反応タイプ: conflict\nコメント: 覚悟を決めよ。"
    comments = await simulate_character_reactions_async(
        journal=hero_journal,
        other_characters=chars,
        llm=mock_llm,
        max_reactions=2,
    )
    assert len(comments) == 2
    for c in comments:
        assert c.from_character_name in ["魔王", "賢者"]
        assert c.reaction_type in ["empathy", "conflict", "irony", "support", "suspicion"]


@pytest.mark.asyncio
async def test_process_scene_async_with_repo(async_db):
    """Step 19-20の検証: process_scene_async による一連の生成とDB保存"""
    session_factory = async_db
    async with session_factory() as session:
        repo = SocialRepository(session)
        mock_llm = MagicMock()
        mock_llm.generate.return_value = "テスト内面テキスト。感情豊かに表現します。"
        manager = SocialInteractionManager(llm_adapter=mock_llm, social_repo=repo)

        chars = [
            {"id": "hero", "name": "主人公", "role": "主人公"},
            {"id": "rival", "name": "ライバル", "role": "好敵手"},
        ]

        result = await manager.process_scene_async(
            book_id=1,
            ep_num=1,
            scene_text="激戦の末に両者は剣を収めた。",
            characters=chars,
        )
        await session.commit()

        assert result["success"] is True
        assert len(result["journals"]) == 2
        assert len(result["comments"]) >= 2

        # DBに日記が保存されているか検証
        journals_in_db = await repo.get_journals(book_id=1, episode_num=1)
        assert len(journals_in_db) == 2

        # DBにコメントが保存されているか検証
        comments_in_db = await repo.get_comments(book_id=1, episode_num=1)
        assert len(comments_in_db) >= 2

        # DBに関係性と履歴が保存されているか検証
        rel_in_db = await repo.get_relationship(book_id=1, char_a="主人公", char_b="ライバル")
        assert rel_in_db is not None
        hist_in_db = await repo.get_relationship_history(book_id=1, char_a="主人公", char_b="ライバル")
        assert len(hist_in_db) >= 1


@pytest.mark.asyncio
async def test_listener_and_dynamics_and_graph_sync():
    """Step 21-23の検証: listenerの非同期呼び出し, dynamics_state判定, graph_sync_async"""
    from src.agents.social.dynamics import RelationshipDynamicsCalculator
    from src.agents.social.models import RelationshipMetrics
    from src.agents.social.graph_sync import SocialGraphSyncer
    from src.agents.social.listener import SocialEventListener
    from src.agents.event_bus import AgentEvent

    # 1. dynamics_state 判定検証 (Step 22)
    rel_ally = RelationshipMetrics(char_a="A", char_b="B", trust_score=80.0, tension_score=20.0, affinity_score=85.0)
    assert RelationshipDynamicsCalculator.compute_dynamics_state(rel_ally) == "allies"

    rel_hostile = RelationshipMetrics(char_a="A", char_b="B", trust_score=20.0, tension_score=80.0, affinity_score=20.0)
    assert RelationshipDynamicsCalculator.compute_dynamics_state(rel_hostile) == "hostile"

    # 2. SocialGraphSyncer async 検証 (Step 23)
    mock_age = MagicMock()
    syncer = SocialGraphSyncer(age_client=mock_age)
    sync_res = await syncer.sync_all_async(session=None, journals=[], comments=[], metrics=[rel_ally])
    assert sync_res["success"] is True

    # 3. SocialEventListener の process_scene_async 呼び出し検証 (Step 21)
    mock_manager = MagicMock()
    mock_manager.process_scene_async = AsyncMock(return_value={"journals": [], "comments": []})
    listener = SocialEventListener(manager=mock_manager)

    event = AgentEvent(
        agent="writing",
        payload={"book_id": 1, "ep_num": 2, "scene_text": "テストシーン"},
        correlation_id="test_corr_1",
    )
    await listener.on_writing_completed(event)
    mock_manager.process_scene_async.assert_awaited_once()


def test_generation_tasks_social_repo_wiring():
    """Step 24の検証: generation_tasks.py が SocialRepository を正常にインポート・参照できること"""
    import inspect
    from src.backend.tasks import generation_tasks
    source = inspect.getsource(generation_tasks._generate_orchestrated)
    assert "SocialRepository" in source
    assert "social_repo=social_repo" in source
