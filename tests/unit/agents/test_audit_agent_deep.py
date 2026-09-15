"""src/agents/audit.py の深層単体テスト."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.agents.audit import (
    AbilityConsistencyChecker,
    DeAIAuditor,
    FastPlotScreener,
    InternalLogicValidator,
    LogicalAuditor,
    PlotIntegrityMonitor,
)
from src.models.audit import CausalityLink, LogicalAuditIssueList
from src.models.sharp_edge import SharpEdgeSpec


# ==============================================================================
# 1. FastPlotScreener & AbilityConsistencyChecker Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_fast_plot_screener():
    llm = MagicMock()
    llm.generate_json = AsyncMock(return_value={"metadata": {"is_valid": True, "feedback": "Great plot"}})
    pm = MagicMock()
    pm.build_fast_plot_screen_prompt.return_value = "screen prompt"

    screener = FastPlotScreener(llm=llm, prompt_manager=pm)
    is_valid, feedback = await screener.screen_plot("Detailed blueprint")
    assert is_valid is True
    assert feedback == "Great plot"


@pytest.mark.asyncio
async def test_ability_consistency_checker():
    # Without prompt manager
    checker_no_pm = AbilityConsistencyChecker(llm=MagicMock(), prompt_manager=None)
    is_ok, fb, _ = await checker_no_pm.audit_ability_consistency("bp", "{}", "{}")
    assert is_ok is True
    assert fb == "OK"

    # With prompt manager
    llm = MagicMock()
    llm.generate_json = AsyncMock(
        return_value={"metadata": {"is_consistent": False, "feedback": "Mana overload", "suggestions": "Tone down"}}
    )
    pm = MagicMock()
    pm.build_ability_audit_prompt.return_value = "ability prompt"
    checker = AbilityConsistencyChecker(llm=llm, prompt_manager=pm)
    is_ok, fb, sugg = await checker.audit_ability_consistency("bp", "{}", "{}")
    assert is_ok is False
    assert fb == "Mana overload"
    assert sugg == "Tone down"


# ==============================================================================
# 2. PlotIntegrityMonitor Tests
# ==============================================================================


def test_plot_integrity_monitor_check_scene():
    monitor = PlotIntegrityMonitor()
    characters = {
        "勇者": {"status": "生存"},
        "魔王": {"status": "死亡"},
    }
    # Dead character appears
    issues = monitor.check_scene("魔王は玉座で笑っていた。", characters)
    assert len(issues) == 1
    assert "魔王は死亡している" in issues[0]

    # Living character appears
    clean_issues = monitor.check_scene("勇者は街道を歩いていた。", characters)
    assert len(clean_issues) == 0


@pytest.mark.asyncio
async def test_plot_integrity_monitor_extract_keywords_empty():
    monitor = PlotIntegrityMonitor()
    assert await monitor.extract_keywords("") == []
    assert await monitor.extract_keywords("   ") == []


@pytest.mark.asyncio
async def test_plot_integrity_monitor_check_integrity_shortcuts():
    monitor = PlotIntegrityMonitor()
    # Empty blueprint
    ok, score, res = await monitor.check_integrity([], "", "content")
    assert ok is True
    assert score == 1.0

    # Empty content
    ok2, score2, res2 = await monitor.check_integrity([], "blueprint", "")
    assert ok2 is True
    assert score2 == 1.0


def test_plot_integrity_monitor_calculate_score():
    monitor = PlotIntegrityMonitor()
    all_links = [
        CausalityLink(source="content", cause_entity="A", cause_event="attack", effect_entity="B", effect_event="hurt", confidence=0.9)
    ]
    # No broken chains, no contradictions
    score1 = monitor._calculate_score(broken_chains=[], foreshadowing=[], contradictions=[], all_links=all_links)
    assert score1 >= 0.8

    # With contradictions
    contradictions = ["Contradiction 1"]
    score2 = monitor._calculate_score(broken_chains=[], foreshadowing=[], contradictions=contradictions, all_links=all_links)
    assert score2 < score1


# ==============================================================================
# 3. DeAIAuditor Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_de_ai_auditor_without_pm():
    auditor = DeAIAuditor(prompt_manager=None)
    is_valid, feedback = await auditor.audit("Plain text")
    assert is_valid is True
    assert feedback == "OK"


@pytest.mark.asyncio
async def test_de_ai_auditor_with_edges():
    # If edge is lost
    auditor = DeAIAuditor(prompt_manager=None)
    edge = SharpEdgeSpec(edge_type="sharp_conflict", description="Cruel battle scene")
    # before_content has edge, content does not
    before = "激痛が走り、鮮血が噴き出した。残酷な戦いだった。"
    after = "戦いが終わった。"
    # Legacy check_edges_preserved logic
    is_valid, feedback = await auditor.audit(content=after, before_content=before, edges=[edge])
    assert isinstance(is_valid, bool)
    assert isinstance(feedback, str)


@pytest.mark.asyncio
async def test_de_ai_auditor_with_prompt_manager():
    llm = MagicMock()
    llm.generate_json = AsyncMock(return_value={"metadata": {"is_valid": True, "feedback": "Natural tone"}})
    pm = MagicMock()
    pm.build_critic_feedback_prompt.return_value = "prompt"

    auditor = DeAIAuditor(llm=llm, prompt_manager=pm)
    is_valid, feedback = await auditor.audit("Novel text")
    assert is_valid is True
    assert feedback == "Natural tone"


# ==============================================================================
# 4. InternalLogicValidator & LogicalAuditor Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_internal_logic_validator():
    mock_llm = MagicMock()
    validator = InternalLogicValidator(llm=mock_llm)
    alibi_ok, alibi_issues = await validator.validate_alibi_and_timeline("bp", "script")
    assert alibi_ok is True
    assert alibi_issues == []

    asym_ok, asym_issues = await validator.check_information_asymmetry("past", "curr")
    assert asym_ok is True
    assert asym_issues == []


@pytest.mark.asyncio
async def test_logical_auditor_generate_critic_feedback():
    # Without prompt manager
    auditor_no_pm = LogicalAuditor(pm=None)
    fb1 = await auditor_no_pm.generate_critic_feedback(LogicalAuditIssueList(issues=[]), "draft", "bp")
    assert "Prompt manager not configured" in fb1.rewrite_guidance

    # With prompt manager and callable LLM
    pm = MagicMock()
    pm.build_critic_feedback_prompt = AsyncMock(return_value="critic prompt")
    
    async def mock_llm_call(purpose, prompt):
        res = MagicMock()
        res.metadata = {"rewrite_guidance": "Add more sensory details."}
        return res

    auditor = LogicalAuditor(pm=pm, generate_json=mock_llm_call)
    fb2 = await auditor.generate_critic_feedback(LogicalAuditIssueList(issues=[]), "draft", "bp")
    assert fb2.rewrite_guidance == "Add more sensory details."
