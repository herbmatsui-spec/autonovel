from unittest.mock import AsyncMock, MagicMock

import pytest
from jinja2 import Environment, FileSystemLoader

from config.project_context import ProjectContext
from src.agents.audit import LogicalAuditor
from prompts.manager import PromptManager
from src.models.audit import AuditIssue, LogicalAuditIssueList
from src.services.writing_services import GenerationLoopManager, WritingGenerationContext


@pytest.fixture
def jinja_env():
    from pathlib import Path
    base_dir = Path(__file__).parent.parent.parent.absolute()
    return Environment(loader=FileSystemLoader(str(base_dir / "prompts")))

@pytest.fixture
def prompt_manager(jinja_env):
    return PromptManager(jinja_env)

@pytest.mark.anyio
async def test_build_critic_feedback_prompt(prompt_manager):
    issue_list = LogicalAuditIssueList(
        is_consistent=False,
        issues=[
            AuditIssue(
                category="場所",
                severity="Major",
                description="主人公が突然王都に移動している",
                evidence_past="前話で主人公は森にいた",
                evidence_current="主人公は王都の宿屋で目覚めた",
                constraint_for_next_ep="移動の描写を入れること"
            )
        ],
        overall_severity="Major"
    )
    prompt = await prompt_manager.build_critic_feedback_prompt(
        issue_list=issue_list,
        draft_content="これはドラフト小説本文です。",
        blueprint="これは設計図です。"
    )
    assert isinstance(prompt, str)
    assert "Critic" in prompt
    assert "主人公が突然王都に移動している" in prompt
    assert "これは設計図です。" in prompt

@pytest.mark.anyio
async def test_generate_critic_feedback_success(prompt_manager):
    # Mock LLM Client generate_json
    class MockRes:
        def __init__(self):
            self.success = True
            self.metadata = {
                "has_critical_issues": True,
                "overall_assessment": "場所の矛盾を確認した",
                "directives": [
                    {
                        "issue_category": "場所",
                        "severity": "Major",
                        "problem_description": "場所の移動が急すぎる",
                        "violating_snippet": "王都の宿屋",
                        "correction_instruction": "移動描写を冒頭に挟め"
                    }
                ],
                "rewrite_guidance": "移動描写を追加してリライトしなさい"
            }
    mock_llm = MagicMock()
    mock_llm.generate_json = AsyncMock(return_value=MockRes())

    auditor = LogicalAuditor(
        repo=MagicMock(),
        pm=prompt_manager,
        llm=mock_llm,
        ctx_mgr=MagicMock()
    )

    issue_list = LogicalAuditIssueList(
        is_consistent=False,
        issues=[
            AuditIssue(category="場所", severity="Major", description="突然の移動")
        ],
        overall_severity="Major"
    )

    fb = await auditor.generate_critic_feedback(
        issue_list=issue_list,
        draft_content="本文",
        blueprint="設計図"
    )

    assert fb.has_critical_issues is True
    assert fb.rewrite_guidance == "移動描写を追加してリライトしなさい"
    mock_llm.generate_json.assert_called_once()

@pytest.mark.anyio
async def test_generate_critic_feedback_fallback(prompt_manager):
    # Mock LLM Client generate_json to fail
    class MockRes:
        def __init__(self):
            self.success = False
            self.metadata = {
                "has_critical_issues": True,
                "rewrite_guidance": "突然の移動"
            }
    mock_llm = MagicMock()
    mock_llm.generate_json = AsyncMock(return_value=MockRes())

    auditor = LogicalAuditor(
        repo=MagicMock(),
        pm=prompt_manager,
        llm=mock_llm,
        ctx_mgr=MagicMock()
    )

    issue_list = LogicalAuditIssueList(
        is_consistent=False,
        issues=[
            AuditIssue(category="場所", severity="Major", description="突然の移動")
        ],
        overall_severity="Major"
    )

    fb = await auditor.generate_critic_feedback(
        issue_list=issue_list,
        draft_content="本文",
        blueprint="設計図"
    )

    assert fb.has_critical_issues is True
    assert "突然の移動" in fb.rewrite_guidance
    assert "フォールバック" not in fb.rewrite_guidance  # checks fallback mechanism works
    mock_llm.generate_json.assert_called_once()

@pytest.mark.anyio
async def test_phase_critic_filtering(prompt_manager):
    # Test _phase_critic respects severity threshold
    mock_llm = MagicMock()
    mock_llm.generate_json = AsyncMock()

    manager = GenerationLoopManager(
        repo=MagicMock(),
        llm=mock_llm,
        pm=prompt_manager,
        critique=LogicalAuditor(pm=prompt_manager),
        narrative=MagicMock(),
        config=MagicMock()
    )
    # Ensure prompt_manager is explicitly set in case it's not handled in __init__
    manager.prompt_manager = prompt_manager
    # LogicAuditor inside manager needs the prompt_manager
    if hasattr(manager, 'critique') and manager.critique:
        manager.critique.prompt_manager = prompt_manager

    # Set threshold to Major
    ProjectContext.set_setting("actor_critic_severity_threshold", "Major")
    ProjectContext.set_setting("actor_critic_enabled", True)

    gen_ctx = WritingGenerationContext()

    # 1. Minor failure (should be filtered out, returning False)
    failures_minor = [{"rule": "場所", "gap": "些細な矛盾", "fragment": "...", "severity": "Minor"}]
    triggered = await manager._phase_critic(
        ac_iter=0,
        ep_num=1,
        draft_content="本文",
        blueprint="設計図",
        failures=failures_minor,
        gen_ctx=gen_ctx,
        reporter=MagicMock()
    )
    assert triggered is False
    mock_llm.generate_json.assert_not_called()

    # 2. Major failure (should trigger critic feedback, return True)
    class MockRes:
        def __init__(self):
            self.success = True
            self.metadata = {
                "has_critical_issues": True,
                "overall_assessment": "Major issue found",
                "directives": [],
                "rewrite_guidance": "Please rewrite"
            }
    mock_llm.generate_json = AsyncMock(return_value=MockRes())

    failures_major = [{"rule": "場所", "gap": "大きな矛盾", "fragment": "...", "severity": "Major"}]
    triggered = await manager._phase_critic(
        ac_iter=0,
        ep_num=1,
        draft_content="本文",
        blueprint="設計図",
        failures=failures_major,
        gen_ctx=gen_ctx,
        reporter=MagicMock()
    )
    assert triggered is True
    assert "Please rewrite" in gen_ctx.feedback_patch
    mock_llm.generate_json.assert_called_once()

    ProjectContext.reset_overrides()
