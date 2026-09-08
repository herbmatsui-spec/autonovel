"""Unit tests for regeneration directive and ActionableDiff integration (Step 61-63)."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.agents.specialists.adapter import AuditAggregatorNode
from src.agents.specialist_auditor_base import SpecialistAuditResult, ActionableDiff
from src.services.audit_aggregator import BookScoreResult
from src.agents.orchestrator import AgentContext, AgentName
from src.agents.prompt_composer import PromptComposer


def test_adapter_to_agent_result_injects_actionable_diffs():
    node = AuditAggregatorNode()

    # Construct BookScoreResult with score < 70 on lowest dimension "reader_hook"
    raw_results = {
        "reader_hook": SpecialistAuditResult(
            specialist_name="reader_hook",
            score=55.0,
            feedback={"note": "poor hook"},
            suggestions=["つかみを強化"],
            actionable_diffs=[
                ActionableDiff(
                    location="冒頭第1段落",
                    original_quote="彼は歩いた。",
                    improved_suggestion="なぜ誰もいないのか？ 彼は歩き続けた。",
                    rationale="冒頭に謎を付与"
                )
            ]
        ),
        "structure": SpecialistAuditResult(
            specialist_name="structure",
            score=80.0,
        )
    }
    score_res = BookScoreResult(
        overall=65.0,
        by_specialist={"reader_hook": 55.0, "structure": 80.0},
        raw=raw_results
    )

    ctx = AgentContext(book_id=1, branch_id=1, ep_num=1)
    agent_result = node.to_agent_result(score_res, ctx, min_pass_score=70.0, max_retries=2)

    assert agent_result.next_agent == AgentName.WRITING
    assert agent_result.should_retry is True

    directive = agent_result.artifacts["regeneration_directive"]
    assert "【再生成指示 - 重点改善項目: reader_hook】" in directive
    assert "【具体的改稿サンプル(Actionable Diffs)】" in directive
    assert "なぜ誰もいないのか？" in directive
    assert agent_result.artifacts["regeneration_focus"] == ["reader_hook"]
    assert len(agent_result.artifacts["actionable_diffs"]) == 1


@pytest.mark.asyncio
async def test_prompt_composer_prepends_regeneration_directive():
    mock_agent = MagicMock()
    mock_pm = MagicMock()
    mock_pm.build_final_writing_prompt = AsyncMock(return_value="元のプロンプト本文")
    mock_agent.prompt_manager = mock_pm

    composer = PromptComposer(agent=mock_agent)
    context = {
        "regeneration_directive": "【具体的改稿サンプル】冒頭に謎を追加すること",
        "plot": {},
        "target_word_count": 2000,
    }

    final_prompt = await composer.compose_writing_prompt(book_id=1, ep_num=1, context=context)

    assert "【最優先・再生成修正ディレクティブ】" in final_prompt
    assert "【具体的改稿サンプル】冒頭に謎を追加すること" in final_prompt
    assert "元のプロンプト本文" in final_prompt
