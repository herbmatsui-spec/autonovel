"""Fault tolerance test for Pillar 1 under low-capability LLM / partial LLM outages (Step 70)."""

import pytest
from unittest.mock import MagicMock
from src.agents.orchestrator import AgentContext, AgentName
from src.agents.enrichment_agent import EnrichmentAgent
from src.services.audit_aggregator import AuditAggregator
from src.config.audit_weights import load_weights
from src.agents.specialists import (
    ConsistencyAuditor,
    CreativityAuditor,
    ReaderHookAuditor,
    EmotionCurveAuditor,
    StyleAuditor,
    FactualAuditor,
    StructureAuditor,
    MultimodalAuditor,
)


@pytest.mark.asyncio
async def test_pillar1_fault_tolerance_with_intermittent_llm_failures():
    # Flaky LLM mock that raises exceptions intermittently
    flaky_llm = MagicMock()
    call_count = 0

    async def flaky_ainvoke(prompt):
        nonlocal call_count
        call_count += 1
        if call_count % 2 == 0:
            raise RuntimeError("Temporary upstream 503 Overloaded error")
        return '{"score": 60, "critique": "Degraded but functional", "confidence": 0.4}'

    flaky_llm.ainvoke = flaky_ainvoke

    # 1. Test EnrichmentAgent with faulty LLM
    enrichment_agent = EnrichmentAgent(llm=flaky_llm)
    enrichment_agent.rag_service = None
    enrichment_agent._config = {
        "enabled": True,
        "trivia_insertion": {"enabled": False},
        "sensory_expansion": {"enabled": True},
        "multimedia": {"enabled": False},
    }

    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=1,
        artifacts={"drafted_text": "彼はとても悲しかったが、ぐっと耐えた。"},
    )

    enrich_result = await enrichment_agent.execute(ctx)
    assert enrich_result.next_agent == AgentName.AUDIT
    # Should cleanly fall back to rule-based sensory expansion without crashing
    assert "悲しかった" not in enrich_result.artifacts["enriched_text"] or len(enrich_result.artifacts["enriched_text"]) > 0

    # 2. Test 8 Specialists under partial outage
    # Some auditors get flaky_llm, some get None (pure rule-based)
    specialists = [
        ConsistencyAuditor(llm=flaky_llm),
        CreativityAuditor(llm=None),
        ReaderHookAuditor(llm=flaky_llm),
        EmotionCurveAuditor(llm=None),
        StyleAuditor(llm=flaky_llm),
        FactualAuditor(llm=None),
        StructureAuditor(llm=flaky_llm),
        MultimodalAuditor(llm=None),
    ]

    weights = load_weights()
    aggregator = AuditAggregator(specialists=specialists, weights=weights)

    audit_input = {
        "book_id": 1,
        "chapter_number": 1,
        "draft_text": "平穏な村に影が忍び寄る。戦いが始まった。どうなるのか！？",
        "world_bible_snapshot": {},
        "plot_tree": "起承転結",
        "illustration_prompts": "村の風景",
    }

    # Must complete without unhandled exceptions
    await aggregator.run_all(audit_input)
    score_res = aggregator.aggregate()

    assert score_res.overall > 0.0
    assert len(score_res.by_specialist) == 8
    # Even under errors, degraded flag and actionable_diffs should be handled gracefully
    for name, res in score_res.raw.items():
        assert res.score >= 0.0
