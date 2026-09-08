"""E2E pipeline integration test for Pillar 1 (Step 68-69).

Tests the full lifecycle of a long chapter (8000+ chars):
1. Raw drafted text
2. EnrichmentAgent (trivia insertion & sensory expansion)
3. 8 Specialist Auditors parallel audit with NovelSectionExtractor
4. AuditAggregator and Actionable Diff extraction
5. Targeted regeneration directive formation and PromptComposer injection
6. Quality metric assertions (syntax integrity, no broken punctuation).
"""

import pytest
import re
from unittest.mock import AsyncMock, MagicMock
from src.agents.orchestrator import AgentContext, AgentName
from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.specialists.adapter import AuditAggregatorNode
from src.services.audit_aggregator import AuditAggregator, BookScoreResult
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
from src.agents.prompt_composer import PromptComposer


@pytest.fixture
def long_novel_draft():
    """8000+ chars draft with some abstract emotions and plot progression."""
    ki = (
        "なぜ少女は一人で冷たい雨の中に立ち尽くしていたのか？\n"
        "夜の街は静まり返り、街灯の薄暗い光が濡れた舗道を照らしていた。" * 60 + "\n"
        "彼はとても悲しかったが、ぐっと奥歯を噛み締めて前を向いた。\n"
    )
    sho = (
        "手がかりを求めて、古びた大図書館の地下迷宮へと潜入した。" * 90 + "\n"
        "探索を続けるうちに、壁に刻まれた古代文字を発見した。\n"
    )
    ten = (
        "祭壇の広間で、白銀の甲冑を纏った騎士エリスが聖剣を抜いた！ 蒼い光が闇を切り裂く。\n"
        "激しい剣戟の音が響き渡り、火花が激しく夜を焦がした。" * 90 + "\n"
    )
    ketsu = (
        "強敵を退け、二人は静かに息を整えた。" * 60 + "\n"
        "瓦礫の山が突然蠢き、背後から不気味な黒い影が現れた！ 一体どうなるのか！？"
    )

    full_draft = ki + sho + ten + ketsu
    assert len(full_draft) >= 8000
    return full_draft


@pytest.mark.asyncio
async def test_pillar1_full_pipeline_e2e(long_novel_draft):
    # --- Step 1: Enrichment (Sensory & Trivia) ---
    enrichment_agent = EnrichmentAgent()
    # Mock RAG & Trivia to avoid external dependencies
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
        artifacts={"drafted_text": long_novel_draft},
    )

    enrich_result = await enrichment_agent.execute(ctx)
    assert enrich_result.next_agent == AgentName.AUDIT
    enriched_text = enrich_result.artifacts["enriched_text"]
    assert len(enriched_text) >= len(long_novel_draft)

    # --- Quality Assertion 1: Syntax Integrity ---
    assert "。が" not in enriched_text
    assert "。。" not in enriched_text
    assert "、。" not in enriched_text
    assert "、が" not in enriched_text

    # --- Step 2: 8 Specialist Auditors Parallel Audit ---
    specialists = [
        ConsistencyAuditor(),
        CreativityAuditor(),
        ReaderHookAuditor(),
        EmotionCurveAuditor(),
        StyleAuditor(),
        FactualAuditor(),
        StructureAuditor(),
        MultimodalAuditor(),
    ]

    from src.config.audit_weights import load_weights
    weights = load_weights()
    aggregator = AuditAggregator(specialists=specialists, weights=weights)
    audit_input = {
        "book_id": 1,
        "chapter_number": 1,
        "draft_text": enriched_text,
        "world_bible_snapshot": {
            "characters": [{"name": "エリス", "role": "騎士"}],
        },
        "plot_tree": "導入→調査→決戦→引き",
        "illustration_prompts": "白銀の甲冑を纏った騎士エリスが聖剣を抜くクライマックスシーン。",
    }

    await aggregator.run_all(audit_input)
    score_result = aggregator.aggregate()

    # --- Quality Assertion 2: All 8 specialists evaluated ---
    assert len(score_result.by_specialist) == 8
    assert score_result.overall > 0.0
    assert "reader_hook" in score_result.by_specialist
    assert "structure" in score_result.by_specialist

    # Reader hook must pick up ending cliffhanger even in 8000+ chars
    hook_res = score_result.raw["reader_hook"]
    assert hook_res.score > 25.0

    # --- Step 3: Adapter Conversion & Actionable Diff Generation ---
    adapter_node = AuditAggregatorNode()
    # Force low score scenario to test regeneration directive
    test_score_result = BookScoreResult(
        overall=58.0,
        by_specialist=score_result.by_specialist,
        raw=score_result.raw,
    )

    agent_result = adapter_node.to_agent_result(
        test_score_result,
        ctx,
        min_pass_score=70.0,
        max_retries=2,
    )

    assert agent_result.next_agent == AgentName.WRITING
    assert agent_result.should_retry is True

    directive = agent_result.artifacts["regeneration_directive"]
    assert "【再生成指示 - 重点改善項目:" in directive
    assert len(agent_result.artifacts["regeneration_focus"]) >= 1

    # --- Step 4: PromptComposer Integration ---
    mock_writing_agent = MagicMock()
    mock_pm = MagicMock()
    mock_pm.build_final_writing_prompt = AsyncMock(return_value="[ベース執筆プロンプト]")
    mock_writing_agent.prompt_manager = mock_pm

    composer = PromptComposer(agent=mock_writing_agent)
    writing_context = {
        "regeneration_directive": directive,
        "plot": {},
        "target_word_count": 3000,
    }

    final_writing_prompt = await composer.compose_writing_prompt(
        book_id=1, ep_num=1, context=writing_context
    )

    # --- Quality Assertion 3: Directive prepended at very top ---
    assert final_writing_prompt.startswith("==================================================\n【最優先・再生成修正ディレクティブ】")
    assert "[ベース執筆プロンプト]" in final_writing_prompt
