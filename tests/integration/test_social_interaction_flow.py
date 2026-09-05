"""Integration test for Social Interaction Dynamics Flow (Step 54).

Verifies the end-to-end flow:
1. 'writing.completed' event is emitted on the EventBus.
2. SocialEventListener triggers SocialInteractionManager.process_scene().
3. Journals, comments, and relationship metric updates are generated.
4. SocialGraphSyncer synchronizes nodes and edges to Apache AGE.
5. ContextBuilderAgent injects the updated social relationships into the next episode's writing context.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.event_bus import EventBus, AgentEvent
from src.agents.social.manager import SocialInteractionManager
from src.agents.social.listener import register_social_listener
from src.agents.context_builder_agent import ContextBuilderAgent
from src.agents.orchestrator import AgentContext


@pytest.mark.asyncio
async def test_social_interaction_end_to_end_flow():
    """Step 54: 執筆完了 → ジャーナル・コメント生成 → AGE同期 → 次章コンテキスト反映の一連フロー検証."""
    event_bus = EventBus()
    mock_age = MagicMock()
    
    # 1. Setup SocialInteractionManager & Listener
    mock_session = MagicMock()
    manager = SocialInteractionManager(age_client=mock_age)
    listener = register_social_listener(
        event_bus, manager, session_factory=lambda: mock_session, graph_name="novel_graph"
    )


    characters = [
        {"id": "hero", "name": "アルカディア", "role": "若き勇者"},
        {"id": "rival", "name": "ヴォルケイン", "role": "冷徹な好敵手"},
    ]

    scene_text = (
        "王都中央広場での処刑を阻止すべく、アルカディアは剣を抜いた。"
        "しかし立ちはだかったのは宿敵ヴォルケインだった。「貴様の甘さがこの混乱を招いたのだ」と冷笑する。"
    )

    # 2. Emit writing.completed for Episode 1
    event = AgentEvent(
        agent="writing.completed",
        payload={
            "book_id": 101,
            "ep_num": 1,
            "drafted_text": scene_text,
            "characters": characters,
        },
        correlation_id="flow_test_corr_1",
    )
    await event_bus.publish_sync(event)

    # 3. Verify that Manager processed the scene
    relationships = manager.get_all_relationships_for_character("アルカディア")
    assert len(relationships) >= 1
    rel = relationships[0]
    # Check that relationship scores moved from initial defaults (50.0)
    assert rel.last_interaction_ep == 1
    assert rel.tension_score != 50.0 or rel.trust_score != 50.0

    # 4. Verify Apache AGE sync was invoked
    assert mock_age.upsert_node.call_count >= 2
    assert mock_age.upsert_edge.call_count >= 2

    # 5. Build context for Episode 2 using ContextBuilderAgent
    repo = MagicMock()
    repo.get_plot = AsyncMock(return_value=MagicMock(
        summary="第2話: 囚われた仲間を救うため、森の奥深くへ向かう。",
        detailed_blueprint="アルカディアはヴォルケインとの決着を持ち越し、森へ向かう。",
    ))
    repo.get_book = AsyncMock(return_value=MagicMock())
    c1 = MagicMock()
    c1.name = "アルカディア"
    c1.role = "若き勇者"
    c1.to_safe_dict.return_value = {"location": "迷いの森", "status": "探索中"}
    c2 = MagicMock()
    c2.name = "ヴォルケイン"
    c2.role = "冷徹な好敵手"
    c2.to_safe_dict.return_value = {"location": "王都", "status": "追跡開始"}
    repo.get_all_characters = AsyncMock(return_value=[c1, c2])
    repo.get_chapter = AsyncMock(return_value=None)

    builder = ContextBuilderAgent(
        social_manager=manager,
        age_client=mock_age,
    )
    ctx = AgentContext(
        book_id=101,
        branch_id=1,
        ep_num=2,
        artifacts={"repo": repo, "target_word_count": 2500},
    )

    agent_result = await builder.execute(ctx)
    assert agent_result.error is None
    writing_ctx = agent_result.artifacts["writing_context"]
    dynamic_ctx = writing_ctx.get("char_dynamic_ctx", "")

    # 6. Verify that social relationship dynamics are injected into next episode context
    assert "登場人物間の動的心理関係性" in dynamic_ctx
    assert "アルカディア ⇔ ヴォルケイン" in dynamic_ctx
    assert "信頼度=" in dynamic_ctx
    assert "緊張度=" in dynamic_ctx
