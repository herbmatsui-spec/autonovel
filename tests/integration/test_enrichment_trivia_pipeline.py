# tests/integration/test_enrichment_trivia_pipeline.py
"""Integration tests for EnrichmentAgent trivia insertion pipeline (Step 11)."""
import pytest
from unittest.mock import MagicMock, AsyncMock
from src.agents.orchestrator import AgentContext, AgentName
from src.agents.enrichment_agent import EnrichmentAgent


@pytest.mark.asyncio
async def test_enrichment_agent_trivia_full_execution():
    """EnrichmentAgent.execute() を通じたトリビアリライト統合実行テスト"""
    mock_llm = MagicMock()
    async def fake_ainvoke(prompt):
        if "トリビア" in prompt or "世界観" in prompt or "書き換え" in prompt:
            return "かつて竜の眠る地と称された広場には、今なお神秘の風が吹き抜けていた。"
        return "頬を伝う冷たい風を感じた。"
    mock_llm.ainvoke = fake_ainvoke

    mock_rag = MagicMock()
    async def fake_query(*args, **kwargs):
        return [
            {
                "fact": "広場は太古の竜の寝床であったとされる。",
                "source_type": "world_bible",
                "entity": "中央広場",
            }
        ]
    mock_rag.query_trivia_candidates = fake_query

    mock_repo = MagicMock()

    agent = EnrichmentAgent(llm=mock_llm, rag_service=mock_rag, repo=mock_repo)
    # 五感拡充等は一旦バイパスしてトリビア挿入を純粋検証
    agent._config["enabled"] = True
    agent._config["trivia_insertion"]["enabled"] = True
    agent._config["sensory_expansion"]["enabled"] = False
    agent._config["citation_attachment"]["enabled"] = False
    agent._config["multimedia_scenarios"]["enabled"] = False

    draft = "勇者は中央広場に到着した。\n\n人々が慌ただしく行き交っていた。"
    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=1,
        artifacts={
            "drafted_text": draft,
            "writing_context": {
                "characters": ["勇者"],
                "location": "中央広場",
                "key_items": ["聖剣"],
                "pov": "third_person",
            },
        },
    )

    result = await agent.execute(ctx)

    assert result.next_agent == AgentName.AUDIT
    assert "enriched_text" in result.artifacts
    enriched_text = result.artifacts["enriched_text"]
    assert "かつて竜の眠る地と称された" in enriched_text

    meta = result.artifacts.get("enrichment_metadata", {})
    assert "trivia" in meta
    trivia_meta = meta["trivia"]
    assert len(trivia_meta) >= 1
    assert trivia_meta[0]["entity"] == "中央広場"
    assert "竜の寝床" in trivia_meta[0]["original"]
    assert "竜の眠る地" in trivia_meta[0]["enriched"]
    assert trivia_meta[0]["tokens"] > 0
