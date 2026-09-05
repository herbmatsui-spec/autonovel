"""Integration test for Writing -> Enrichment -> AuditAggregator Pipeline Chain (Step 62).

Verifies that:
1. WritingAgent produces a drafted text and forwards to ENRICHMENT.
2. EnrichmentAgent enriches the drafted text (sensory expansion / token budget) and forwards to AUDIT.
3. AuditAggregatorNode receives enriched_text and aggregates evaluations from specialist auditors.
"""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.orchestrator import AgentContext, AgentName
from src.agents.writing.agent import WritingAgent
from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.specialists.adapter import AuditAggregatorNode



@pytest.mark.asyncio
async def test_writing_enrichment_audit_chain():
    """Step 62: 執筆 → エンリッチメント → 8専門監査ノードの一連の連動を検証."""
    # 1. Setup WritingAgent with Mock Generator
    mock_generator = MagicMock()
    mock_generator.generate_episodes_pipeline = AsyncMock(return_value=(1500, []))

    mock_chapter = MagicMock()
    mock_chapter.content = "アルカディアは悲しかった。しかし剣を抜いた。"
    mock_repo = MagicMock()
    mock_repo.get_chapter = AsyncMock(return_value=mock_chapter)
    mock_repo.save_chapter = AsyncMock()

    writing_agent = WritingAgent(
        repo=mock_repo,
    )
    writing_agent._generator = mock_generator

    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=1,
        artifacts={
            "writing_context": {
                "plot": {"summary": "第1話"},
                "pov": "三人称",
                "scene_context": "雨の広場",
            },
            "target_word_count": 1000,
        },
    )


    # 1. Execute WritingAgent
    writing_result = await writing_agent.execute(ctx)
    assert writing_result.next_agent == AgentName.ENRICHMENT
    assert "drafted_text" in writing_result.artifacts
    drafted = writing_result.artifacts["drafted_text"]
    assert "悲しかった" in drafted

    # 2. Forward to EnrichmentAgent
    ctx.artifacts.update(writing_result.artifacts)

    mock_enrich_llm = MagicMock()
    mock_enrich_llm.generate.return_value = "冷たい雨が頬を濡らし、胸の奥に鉛のような痛みが広がっていた。"

    enrichment_agent = EnrichmentAgent(llm=mock_enrich_llm)
    enrichment_agent._config["enabled"] = True
    enrichment_agent._config["sensory_expansion"] = {"enabled": True}
    enrichment_agent._config["trivia_insertion"] = {"enabled": False}
    enrichment_agent._config["citation_attachment"] = {"enabled": False}

    enrichment_result = await enrichment_agent.execute(ctx)
    assert enrichment_result.next_agent == AgentName.AUDIT
    assert "enriched_text" in enrichment_result.artifacts
    enriched = enrichment_result.artifacts["enriched_text"]
    assert "胸の奥に鉛のような痛みが広がっていた" in enriched
    assert "[visual]" not in enriched

    # 3. Forward to AuditAggregatorNode
    ctx.artifacts.update(enrichment_result.artifacts)
    audit_node = AuditAggregatorNode()

    audit_result = await audit_node.execute(ctx)
    assert audit_result.error is None
    # 監査結果が格納されていること
    assert "audit_report" in audit_result.artifacts
    assert "audit_score" in audit_result.artifacts
    assert "specialist_scores" in audit_result.artifacts
    assert audit_result.artifacts["audit_score"] > 0
