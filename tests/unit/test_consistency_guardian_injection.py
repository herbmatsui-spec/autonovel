import pytest
from unittest.mock import MagicMock
from src.services.writing_services import GenerationLoopManager, WritingGenerationContext, WritingContext
from src.models import BookDbModel

# Dummy dependencies for GenerationLoopManager
dummy_repo = MagicMock()
dummy_llm = MagicMock()
dummy_pm = MagicMock()
dummy_critique = MagicMock()
dummy_narrative = MagicMock()
dummy_config = MagicMock()

@pytest.mark.asyncio
async def test_consistency_guardian_injection_adds_string(monkeypatch):
    # Mock get_consistency_prompt_injection to return a known string
    def mock_get_injection(book_id, branch_id=1, ep_num=None):
        return "[整合性チェック結果]\n1. [HIGH] テスト: テスト説明"
    monkeypatch.setattr("src.consistency.guardian_hook.get_consistency_prompt_injection", mock_get_injection)

    # Create a minimal WritingContext
    book = BookDbModel(id=1, title="Test", genre="fantasy", concept="", synopsis="", target_eps=10)
    ctx = WritingContext(book=book, branch_id=1, book_id=1, current_tension=0, plot=None, prose_samples=[], prev_world_state={})
    # Call _phase_prepare_context via a dummy manager
    manager = GenerationLoopManager(dummy_repo, dummy_llm, dummy_pm, dummy_critique, dummy_narrative, dummy_config)
    # We need to provide sys_inst and fw_prompt; use simple strings
    sys_inst_base = "BASE_SYS_INST"
    fw_prompt_base = "BASE_FW_PROMPT"
    gen_ctx, _, _, _, _ = await manager._phase_prepare_context(
        ep_num=1,
        ctx=ctx,
        sys_inst=sys_inst_base,
        fw_prompt=fw_prompt_base,
        is_easy_mode=False,
        reporter=None
    )
    # Check that the generated sys_inst contains the base and the injection
    assert sys_inst_base in gen_ctx.sys_inst
    assert "[整合性チェック結果]" in gen_ctx.sys_inst
    assert "1. [HIGH] テスト: テスト説明" in gen_ctx.sys_inst

@pytest.mark.asyncio
async def test_consistency_guardian_injection_respects_flag(monkeypatch):
    # Mock get_consistency_prompt_injection to return a known string
    def mock_get_injection(book_id, branch_id=1, ep_num=None):
        return "[整合性チェック結果]\n1. [HIGH] テスト: テスト説明"
    monkeypatch.setattr("src.consistency.guardian_hook.get_consistency_prompt_injection", mock_get_injection)

    # Mock ProjectContext.get_setting to return False for consistency_guardian_enabled
    # We need to patch where it's used: in writing_services, they use ProjectContext.get_setting
    # Capture the original function before monkeypatching
    import src.services.writing_services as ws
    original_get_setting = ws.ProjectContext.__dict__.get("get_setting")
    def mock_get_setting(key, default=None):
        if key == "consistency_guardian_enabled":
            return False
        # For other keys, delegate to the actual ProjectContext.get_setting
        if original_get_setting:
            return original_get_setting(key, default)
        return default
    monkeypatch.setattr("src.services.writing_services.ProjectContext.get_setting", mock_get_setting)

    # Create a minimal WritingContext
    book = BookDbModel(id=1, title="Test", genre="fantasy", concept="", synopsis="", target_eps=10)
    ctx = WritingContext(book=book, branch_id=1, book_id=1, current_tension=0, plot=None, prose_samples=[], prev_world_state={})
    manager = GenerationLoopManager(dummy_repo, dummy_llm, dummy_pm, dummy_critique, dummy_narrative, dummy_config)
    sys_inst_base = "BASE_SYS_INST"
    fw_prompt_base = "BASE_FW_PROMPT"
    gen_ctx, _, _, _, _ = await manager._phase_prepare_context(
        ep_num=1,
        ctx=ctx,
        sys_inst=sys_inst_base,
        fw_prompt=fw_prompt_base,
        is_easy_mode=False,
        reporter=None
    )
    # Should NOT contain the injection
    assert sys_inst_base in gen_ctx.sys_inst
    assert "[整合性チェック結果]" not in gen_ctx.sys_inst
    assert "1. [HIGH] テスト: テスト説明" not in gen_ctx.sys_inst

@pytest.mark.asyncio
async def test_consistency_guardian_injection_handles_empty(monkeypatch):
    # Mock get_consistency_prompt_injection to return empty string
    def mock_get_injection(book_id, branch_id=1, ep_num=None):
        return ""
    monkeypatch.setattr("src.consistency.guardian_hook.get_consistency_prompt_injection", mock_get_injection)

    book = BookDbModel(id=1, title="Test", genre="fantasy", concept="", synopsis="", target_eps=10)
    ctx = WritingContext(book=book, branch_id=1, book_id=1, current_tension=0, plot=None, prose_samples=[], prev_world_state={})
    manager = GenerationLoopManager(dummy_repo, dummy_llm, dummy_pm, dummy_critique, dummy_narrative, dummy_config)
    sys_inst_base = "BASE_SYS_INST"
    fw_prompt_base = "BASE_FW_PROMPT"
    # Disable style learning to isolate the consistency guardian test
    def mock_get_setting(key, default=None):
        if key == "style_learning_enabled":
            return False
        if key == "consistency_guardian_enabled":
            return True  # we are testing consistency guardian
        # For other keys, delegate to the actual ProjectContext.get_setting
        import src.services.writing_services as ws
        original_get_setting = ws.ProjectContext.__dict__.get("get_setting")
        if original_get_setting:
            return original_get_setting(key, default)
        return default
    monkeypatch.setattr("src.services.writing_services.ProjectContext.get_setting", mock_get_setting)
    # Re-run with style learning off
    gen_ctx2, _, _, _, _ = await manager._phase_prepare_context(
        ep_num=1,
        ctx=ctx,
        sys_inst=sys_inst_base,
        fw_prompt=fw_prompt_base,
        is_easy_mode=False,
        reporter=None
    )
    # Should be exactly base (no extra newlines)
    assert gen_ctx2.sys_inst == sys_inst_base
