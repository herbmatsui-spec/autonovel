"""Unit tests for Social Interaction Models, Discovery, and Journals (Steps 45-48)."""
from __future__ import annotations

import pytest

from src.agents.social.models import JournalEntry, SocialComment, RelationshipMetrics
from src.agents.social.manager import SocialInteractionManager
from src.agents.social.friends_discovery import discover_related_characters
from src.agents.social.journals import generate_multi_perspective_journals


def test_social_models_serialization():
    """Step 45: ソーシャルデータモデルの検証."""
    journal = JournalEntry(
        entry_id="j_1",
        character_id="hero",
        character_name="アルカディア",
        theme="決意",
        emotion="緊張",
        content="明日王都を出発する。",
    )
    assert journal.character_name == "アルカディア"
    assert journal.book_id == 1

    comment = SocialComment(
        comment_id="c_1",
        journal_id="j_1",
        from_character_id="rival",
        from_character_name="ヴォルケイン",
        reaction_type="irony",
        content="道中で野垂れ死ぬなよ。",
        trust_delta=-5.0,
        tension_delta=10.0,
    )
    assert comment.reaction_type == "irony"
    assert comment.tension_delta == 10.0


def test_social_interaction_manager_relationship_tracking():
    """Step 46: 2者間関係性メトリクスの双方向管理検証."""
    manager = SocialInteractionManager()

    # 初期スコアは 50 / 50 / 50
    rel = manager.get_relationship("アルカディア", "エレナ")
    assert rel.trust_score == 50.0
    assert rel.tension_score == 50.0

    # 関係性更新
    updated = manager.update_relationship(
        "エレナ", "アルカディア",
        trust_delta=15.0,
        tension_delta=-10.0,
        affinity_delta=20.0,
        ep_num=2,
    )
    assert updated.trust_score == 65.0
    assert updated.tension_score == 40.0
    assert updated.affinity_score == 70.0
    assert updated.last_interaction_ep == 2

    # 逆順アクセスでも同一メトリクスが返る
    rel_rev = manager.get_relationship("アルカディア", "エレナ")
    assert rel_rev.trust_score == 65.0


def test_friends_discovery_inference():
    """Step 47: 基準キャラからの未登場関連キャラ自動推論検証."""
    base_char = {
        "name": "アルカディア",
        "role": "王国の若き勇者・剣士",
    }
    candidates = discover_related_characters(base_char, count=2)
    assert len(candidates) == 2
    names = [c.name for c in candidates]
    roles = [c.role for c in candidates]
    assert "rival" in roles or "mentor" in roles
    assert len(names) == len(set(names))


def test_multi_perspective_journals_different_views():
    """Step 48: 同一シーンに対する多視点内面独白の差別化検証."""
    scene = "王都広場での反逆者公開裁判と、突如乱入した暗殺者との激闘"
    characters = [
        {"id": "hero", "name": "アルカディア", "role": "正義の勇者"},
        {"id": "rival", "name": "ヴォルケイン", "role": "冷酷な魔王軍ライバル"},
    ]

    journals = generate_multi_perspective_journals(scene, characters, book_id=1, ep_num=1)
    assert len(journals) == 2

    hero_j = next(j for j in journals if j.character_id == "hero")
    rival_j = next(j for j in journals if j.character_id == "rival")

    assert hero_j.emotion != rival_j.emotion
    assert hero_j.content != rival_j.content
    assert "犠牲" in hero_j.content or "勝利" in hero_j.content
    assert "甘い" in rival_j.content or "無力" in rival_j.content


def test_simulate_character_reactions():
    """Step 49: ジャーナルに対する他キャラのリアクション・コメントシミュレーション検証."""
    from src.agents.social.comments import simulate_character_reactions

    journal = JournalEntry(
        entry_id="j_hero_1",
        character_id="hero",
        character_name="アルカディア",
        theme="葛藤",
        emotion="苦悩",
        content="誰も傷つけたくないが、剣を抜くしかないのか。",
    )
    other_chars = [
        {"id": "rival", "name": "ヴォルケイン", "role": "宿敵・ライバル"},
        {"id": "mentor", "name": "ゼノン", "role": "師匠・賢者"},
    ]

    comments = simulate_character_reactions(journal, other_chars, max_reactions=2)
    assert len(comments) == 2

    rival_cmt = next(c for c in comments if c.from_character_id == "rival")
    mentor_cmt = next(c for c in comments if c.from_character_id == "mentor")

    assert rival_cmt.reaction_type == "irony"
    assert rival_cmt.tension_delta > 0
    assert mentor_cmt.reaction_type == "support"
    assert mentor_cmt.trust_delta > 0


def test_relationship_dynamics_calculator():
    """Step 50: 動的関係性推移の時系列計算検証."""
    from src.agents.social.dynamics import RelationshipDynamicsCalculator

    calc = RelationshipDynamicsCalculator()
    comments = [
        SocialComment(
            comment_id="c_1",
            journal_id="j_1",
            from_character_id="char_b",
            from_character_name="ライバル",
            reaction_type="conflict",
            content="衝突する意見",
            trust_delta=-10.0,
            tension_delta=15.0,
        ),
    ]

    # ep 1: 衝突による緊張増大・信頼低下
    metrics_map = calc.calculate_epoch_updates(
        author_name="主人公",
        comments=comments,
        ep_num=1,
    )
    pair = tuple(sorted(["主人公", "ライバル"]))
    assert pair in metrics_map
    m1 = metrics_map[pair]
    assert m1.trust_score < 50.0
    assert m1.tension_score > 50.0


def test_social_graph_syncer_mock():
    """Step 51: Apache AGEへのノード・エッジ同期呼び出し検証."""
    from unittest.mock import MagicMock
    from src.agents.social.graph_sync import SocialGraphSyncer

    mock_age = MagicMock()
    syncer = SocialGraphSyncer(age_client=mock_age)
    session = MagicMock()

    journal = JournalEntry(
        entry_id="j_sync_1",
        character_id="hero",
        character_name="アルカディア",
        content="テスト本文",
    )
    comment = SocialComment(
        comment_id="c_sync_1",
        journal_id="j_sync_1",
        from_character_id="rival",
        from_character_name="ヴォルケイン",
        content="テストコメント",
    )
    metric = RelationshipMetrics(
        char_a="アルカディア",
        char_b="ヴォルケイン",
        trust_score=60.0,
        tension_score=40.0,
    )

    result = syncer.sync_all(
        session=session,
        journals=[journal],
        comments=[comment],
        metrics=[metric],
    )
    assert result["success"] is True
    assert result["synced_journals"] == 1
    assert result["synced_comments"] == 1
    assert result["synced_metrics"] == 1

    # Check that upsert_node and upsert_edge were called
    assert mock_age.upsert_node.call_count >= 3
    assert mock_age.upsert_edge.call_count >= 3


@pytest.mark.asyncio
async def test_social_event_listener_dispatch():
    """Step 52: writing.completed イベント購読とディスパッチ検証."""
    from unittest.mock import MagicMock
    from src.agents.event_bus import EventBus, AgentEvent
    from src.agents.social.listener import register_social_listener

    event_bus = EventBus()
    mock_manager = MagicMock()
    mock_manager.process_scene.return_value = {
        "journals": [{"entry_id": "j_1"}],
        "comments": [{"comment_id": "c_1"}],
    }

    listener = register_social_listener(event_bus, mock_manager)

    event = AgentEvent(
        agent="writing.completed",
        payload={
            "book_id": 1,
            "ep_num": 3,
            "drafted_text": "激戦の末、勝利を手にした。",
            "characters": [{"id": "hero", "name": "アルカディア"}],
        },
        correlation_id="test_corr_123",
    )

    await event_bus.publish_sync(event)

    # Verify process_scene was called with expected arguments
    mock_manager.process_scene.assert_called_once()
    kwargs = mock_manager.process_scene.call_args.kwargs
    assert kwargs["book_id"] == 1
    assert kwargs["ep_num"] == 3
    assert "激戦" in kwargs["scene_text"]


@pytest.mark.asyncio
async def test_context_builder_agent_social_integration():
    """Step 53: ContextBuilderAgent でのソーシャル関係性・ジャーナル注入検証."""
    from unittest.mock import AsyncMock, MagicMock
    from src.agents.context_builder_agent import ContextBuilderAgent
    from src.agents.orchestrator import AgentContext
    from src.agents.social.manager import SocialInteractionManager

    repo = MagicMock()
    repo.get_plot = AsyncMock(return_value=MagicMock(summary="王都の決戦", detailed_blueprint="アルカディアとヴォルケインの対峙"))
    repo.get_book = AsyncMock(return_value=MagicMock())
    char1 = MagicMock(name="アルカディア", role="主人公")
    char1.name = "アルカディア"
    char1.role = "主人公"
    char1.to_safe_dict.return_value = {"location": "王都広場", "status": "臨戦態勢"}
    char2 = MagicMock(name="ヴォルケイン", role="ライバル")
    char2.name = "ヴォルケイン"
    char2.role = "ライバル"
    char2.to_safe_dict.return_value = {"location": "王都広場", "status": "対峙"}
    repo.get_all_characters = AsyncMock(return_value=[char1, char2])
    repo.get_chapter = AsyncMock(return_value=None)

    # SocialManager with relationship
    social_mgr = SocialInteractionManager()
    social_mgr.update_relationship("アルカディア", "ヴォルケイン", trust_delta=-15.0, tension_delta=25.0)

    agent = ContextBuilderAgent(social_manager=social_mgr)
    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=2,
        artifacts={"repo": repo, "target_word_count": 2000},
    )

    result = await agent.execute(ctx)
    writing_ctx = result.artifacts.get("writing_context", {})
    char_dynamic_ctx = writing_ctx.get("char_dynamic_ctx", "")

    # Check that dynamic relationships are included in char_dynamic_ctx
    assert "登場人物間の動的心理関係性" in char_dynamic_ctx
    assert "アルカディア ⇔ ヴォルケイン" in char_dynamic_ctx
    assert "緊張度=75.0" in char_dynamic_ctx



