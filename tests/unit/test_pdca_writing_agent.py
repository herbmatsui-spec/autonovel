"""Tests for WritingAgent PDCA rewriting and ClosedLoopPDCARunner integration (Steps 10-12)."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.writing.agent import WritingAgent
from src.services.pdca_cycle import ClosedLoopPDCARunner
from src.services.audit_aggregator import AuditAggregator, BookScoreResult
from src.agents.specialist_auditor_base import SpecialistAuditResult, ActionableDiff


class DummyChapter:
    def __init__(self, cid: int, ep_num: int, content: str):
        self.id = cid
        self.ep_num = ep_num
        self.content = content


class DummyRepo:
    def __init__(self, content: str = "アルトは剣を抜いた。森は静まり返っていた。"):
        self.chapter = DummyChapter(1, 1, content)
        self.updated_content = None

    async def get_chapter(self, branch_id: int, ep_num: int):
        return self.chapter

    async def update_chapter_content(self, chapter_id: int, new_content: str):
        self.updated_content = new_content
        self.chapter.content = new_content


class DummyLLM:
    def __init__(self, rewritten_output: str = "【改稿後】アルトは錆びついた古代魔導剣を素早く抜いた。静寂の森に刃鳴りが響き渡る。"):
        self.rewritten_output = rewritten_output
        self.last_prompt = None

    async def generate_text(self, prompt: str, system_prompt: str = None, max_tokens: int = 2000, **kwargs):
        self.last_prompt = prompt
        return self.rewritten_output


@pytest.mark.asyncio
async def test_writing_agent_rewrite_with_focus_calls_llm_and_updates_chapter():
    """Step 10: WritingAgent.rewrite_with_focus executes actual LLM rewrite and updates chapter."""
    orig_text = "少年は立ち上がった。"
    repo = DummyRepo(content=orig_text)
    expected_rewrite = "少年は膝の痛みに耐え、歯を食いしばりながら立ち上がった。"
    llm = DummyLLM(rewritten_output=expected_rewrite)

    agent = WritingAgent(repo=repo, llm=llm)

    diffs = [
        {
            "location": "冒頭",
            "original_quote": "少年は立ち上がった。",
            "improved_suggestion": "もっと痛みの描写を加えるべき",
            "rationale": "切迫感を出すため",
        }
    ]

    result = await agent.rewrite_with_focus(
        book_id=1,
        ep_num=1,
        focus="reader_experience",
        params={
            "enhance_hook": True,
            "actionable_diffs": diffs,
        },
    )

    assert result["status"] == "success"
    assert result["original_length"] == len(orig_text)
    assert result["rewritten_length"] == len(expected_rewrite)
    assert result["rewritten_text"] == expected_rewrite
    assert result["diff_ratio"] > 0
    assert "execution_time_ms" in result
    # DB repo updated
    assert repo.updated_content == expected_rewrite
    # Prompt contained instructions and actionable diff
    assert "【修正箇所: 冒頭】" in llm.last_prompt


@pytest.mark.asyncio
async def test_pdca_runner_with_writing_agent_adapter():
    """Step 11: ClosedLoopPDCARunner successfully invokes WritingAgent and completes cycle."""
    repo = DummyRepo(content="暗い夜だった。")
    llm = DummyLLM(rewritten_output="不気味な満月が雲間から覗く、凍てつくような夜だった。")
    writer = WritingAgent(repo=repo, llm=llm)

    # Mock AuditAggregator
    mock_aggregator = MagicMock(spec=AuditAggregator)
    mock_aggregator.run_all = AsyncMock(return_value={})

    # First audit returns 60.0 (below target), second audit returns 80.0
    audit1 = BookScoreResult(
        overall=60.0,
        by_specialist={"reader_hook": 50.0, "style": 70.0},
        calibrated_overall=60.0,
        calibrated_by_specialist={"reader_hook": 50.0, "style": 70.0},
    )
    audit2 = BookScoreResult(
        overall=82.0,
        by_specialist={"reader_hook": 80.0, "style": 84.0},
        calibrated_overall=82.0,
        calibrated_by_specialist={"reader_hook": 80.0, "style": 84.0},
    )

    mock_aggregator.aggregate.side_effect = [audit1, audit1, audit2, audit2]

    runner = ClosedLoopPDCARunner(
        aggregator=mock_aggregator,
        writer=writer,
        target_score=75.0,
        max_cycles=3,
    )

    best_draft, res = await runner.run_pdca_cycle(
        initial_context={
            "draft_text": "暗い夜だった。",
            "book_id": 1,
            "ep_num": 1,
        }
    )

    assert res.converged is True
    assert res.final_score >= 75.0
    assert res.cycle_number >= 1
    assert len(res.history) >= 2
