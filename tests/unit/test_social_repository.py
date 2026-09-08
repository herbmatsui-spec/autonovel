import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.infrastructure.database.models.base_orm import Base
from src.backend.database.models import (
    Book,
    CharacterRelationship,
    CharacterJournal,
    CharacterComment,
    RelationshipHistory,
)
from src.backend.database.social_repository import SocialRepository
from src.agents.social.models import RelationshipMetrics, JournalEntry, SocialComment


@pytest.fixture
async def async_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    # テスト用のダミーBookを作成
    async with session_factory() as session:
        book = Book(id=1, title="Test Novel")
        session.add(book)
        await session.commit()

    yield session_factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_social_models_and_repository_init(async_db):
    """Step 1-6の検証: モデルが正常に生成でき、SocialRepositoryが初期化できること"""
    session_factory = async_db
    async with session_factory() as session:
        repo = SocialRepository(session)
        assert repo._session is session
        async with repo.session_scope() as scoped_session:
            assert scoped_session is session


@pytest.mark.asyncio
async def test_social_repository_relationship_crud(async_db):
    """Step 7-8の検証: upsert_relationship, get_relationship, get_all_relationships"""
    session_factory = async_db
    async with session_factory() as session:
        repo = SocialRepository(session)

        # 1. 初期upsert (char_a="Alice", char_b="Bob")
        m1 = RelationshipMetrics(
            char_a="Alice",
            char_b="Bob",
            trust_score=75.0,
            tension_score=20.0,
            affinity_score=80.0,
            last_interaction_ep=1,
        )
        await repo.upsert_relationship(book_id=1, char_a="Alice", char_b="Bob", metrics=m1)
        await session.commit()

        # 2. 正順での取得
        rel_ab = await repo.get_relationship(book_id=1, char_a="Alice", char_b="Bob")
        assert rel_ab is not None
        assert rel_ab.trust_score == 75.0
        assert rel_ab.affinity_score == 80.0
        assert rel_ab.tension_score == 20.0

        # 3. 逆順での取得
        rel_ba = await repo.get_relationship(book_id=1, char_a="Bob", char_b="Alice")
        assert rel_ba is not None
        assert rel_ba.trust_score == 75.0

        # 4. 更新upsert
        m1_updated = RelationshipMetrics(
            char_a="Alice",
            char_b="Bob",
            trust_score=90.0,
            tension_score=10.0,
            affinity_score=95.0,
            last_interaction_ep=2,
        )
        await repo.upsert_relationship(book_id=1, char_a="Bob", char_b="Alice", metrics=m1_updated)
        await session.commit()

        rel_updated = await repo.get_relationship(book_id=1, char_a="Alice", char_b="Bob")
        assert rel_updated.trust_score == 90.0
        assert rel_updated.last_interaction_ep == 2

        # 5. get_all_relationships
        all_rels = await repo.get_all_relationships(book_id=1)
        assert ("Alice", "Bob") in all_rels
        assert ("Bob", "Alice") in all_rels
        assert all_rels[("Alice", "Bob")].trust_score == 90.0


@pytest.mark.asyncio
async def test_social_repository_history(async_db):
    """Step 9-10の検証: record_history, get_relationship_history"""
    session_factory = async_db
    async with session_factory() as session:
        repo = SocialRepository(session)

        # エピソード1でのスナップショット
        m_ep1 = RelationshipMetrics(
            char_a="Alice",
            char_b="Charlie",
            trust_score=50.0,
            tension_score=30.0,
            affinity_score=55.0,
            last_interaction_ep=1,
        )
        await repo.record_history(
            book_id=1,
            char_a="Alice",
            char_b="Charlie",
            episode_num=1,
            metrics=m_ep1,
            trigger_event="First encounter",
        )

        # エピソード2でのスナップショット
        m_ep2 = RelationshipMetrics(
            char_a="Alice",
            char_b="Charlie",
            trust_score=70.0,
            tension_score=40.0,
            affinity_score=65.0,
            last_interaction_ep=2,
        )
        await repo.record_history(
            book_id=1,
            char_a="Alice",
            char_b="Charlie",
            episode_num=2,
            metrics=m_ep2,
            trigger_event="Battle cooperation",
        )
        await session.commit()

        # 履歴取得 (昇順)
        history = await repo.get_relationship_history(book_id=1, char_a="Alice", char_b="Charlie")
        assert len(history) == 2
        assert history[0]["episode_num"] == 1
        assert history[0]["trust"] == 50.0
        assert history[0]["trigger_event"] == "First encounter"
        assert history[1]["episode_num"] == 2
        assert history[1]["trust"] == 70.0
        assert history[1]["trigger_event"] == "Battle cooperation"


@pytest.mark.asyncio
async def test_social_repository_journals_and_comments(async_db):
    """Step 11-12の検証: save_journal, get_journals, save_comment, get_comments"""
    session_factory = async_db
    async with session_factory() as session:
        repo = SocialRepository(session)

        # 日記保存
        journal = JournalEntry(
            entry_id="j1",
            book_id=1,
            ep_num=1,
            character_id="alice",
            character_name="Alice",
            content="Today was a tough day.",
            emotion="exhausted",
        )
        await repo.save_journal(book_id=1, character_name="Alice", episode_num=1, journal=journal)

        # コメント保存
        comment = SocialComment(
            comment_id="c1",
            journal_id="j1",
            from_character_id="bob",
            from_character_name="Bob",
            reaction_type="support",
            content="Hang in there, Alice!",
        )
        await repo.save_comment(book_id=1, character_name="Bob", episode_num=1, comment=comment)
        await session.commit()

        # 日記取得
        journals = await repo.get_journals(book_id=1, episode_num=1)
        assert len(journals) == 1
        assert journals[0]["character_name"] == "Alice"
        assert journals[0]["entry_text"] == "Today was a tough day."
        assert journals[0]["emotional_state"] == "exhausted"

        # コメント取得
        comments = await repo.get_comments(book_id=1, episode_num=1)
        assert len(comments) == 1
        assert comments[0]["character_name"] == "Bob"
        assert comments[0]["comment_text"] == "Hang in there, Alice!"
        assert comments[0]["topic"] == "support"
