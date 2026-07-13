import os
from unittest.mock import AsyncMock, MagicMock

import pytest
from jinja2 import Environment, FileSystemLoader

from src.backend.engine_prompts import PromptManager
from src.services.writing_services import GenerationLoopManager, WritingGenerationContext


@pytest.fixture
def jinja_env():
    from pathlib import Path
    base_dir = Path(__file__).parent.parent.parent.absolute()
    prompts_dir = base_dir / "prompts"
    templates_dir = prompts_dir / "templates"
    search_paths = [str(prompts_dir)]
    if templates_dir.exists():
        for root, dirs, _ in os.walk(str(templates_dir)):
            search_paths.append(root)
    return Environment(loader=FileSystemLoader(search_paths))

@pytest.fixture
def prompt_manager(jinja_env):
    return PromptManager(jinja_env)

@pytest.mark.asyncio
async def test_build_drafting_prompt(prompt_manager):
    plot_data = {
        "scenes": [{"action": "主人公が修行する", "impact_score": 50}],
        "current_chain_phase": "Hate",
        "detailed_blueprint": "詳細な修行プロット"
    }
    sys_inst, fw_prompt = await prompt_manager.build_drafting_prompt(
        ep_num=1,
        plot_data=plot_data,
        script_text="修行シーンの台本",
        target_word_count=1000,
        char_static_ctx="主人公の静的設定",
        char_dynamic_ctx="主人公の動的設定",
        prev_ctx="前話のあらすじ"
    )
    assert isinstance(sys_inst, str)
    assert isinstance(fw_prompt, str)
    assert "Drafting Agent" in sys_inst
    assert "修行シーンの台本" in fw_prompt
    assert "詳細な修行プロット" in fw_prompt

@pytest.mark.asyncio
async def test_build_polishing_prompt(prompt_manager):
    prompt = await prompt_manager.build_polishing_prompt(
        draft_content="これは初稿です。",
        target_word_count=1000,
        style_key="style_web_standard",
        prose_sample="文体継承サンプル"
    )
    assert isinstance(prompt, str)
    assert "Polishing Agent" in prompt
    assert "これは初稿です。" in prompt
    assert "文体継承サンプル" in prompt
    assert "AI定型句の禁止" in prompt

@pytest.mark.anyio
async def test_polishing_pass_success(prompt_manager):
    # Mock LLM Client
    mock_llm = MagicMock()
    # Mock return value of generate_text
    class MockRes:
        success = True
        story_content = "これは磨き上げられた完成稿の小説本文です。十分に長い文章です。"
    mock_llm.generate_text = AsyncMock(return_value=MockRes())

    # Create GenerationLoopManager
    manager = GenerationLoopManager(
        repo=MagicMock(),
        llm=mock_llm,
        pm=prompt_manager,
        critique=MagicMock(),
        narrative=MagicMock(),
        config=MagicMock()
    )

    gen_ctx = WritingGenerationContext(
        sys_inst="sys",
        fw_prompt="fw",
        style_key="style_web_standard",
        target_word_count=1000,
        enable_polishing=True,
        prose_sample=""
    )

    reporter = MagicMock()

    polished = await manager._polishing_pass(
        ep_num=1,
        draft_content="これは初稿です。",
        gen_ctx=gen_ctx,
        temp=0.7,
        reporter=reporter
    )

    assert polished == "これは磨き上げられた完成稿の小説本文です。十分に長い文章です。"
    mock_llm.generate_text.assert_called_once()

@pytest.mark.anyio
async def test_polishing_pass_fallback(prompt_manager):
    # Mock LLM Client failure or short output
    mock_llm = MagicMock()
    class MockRes:
        success = True
        story_content = "短い"
    mock_llm.generate_text = AsyncMock(return_value=MockRes())

    manager = GenerationLoopManager(
        repo=MagicMock(),
        llm=mock_llm,
        pm=prompt_manager,
        critique=MagicMock(),
        narrative=MagicMock(),
        config=MagicMock()
    )

    gen_ctx = WritingGenerationContext(
        sys_inst="sys",
        fw_prompt="fw",
        style_key="style_web_standard",
        target_word_count=1000,
        enable_polishing=True,
        prose_sample=""
    )

    polished = await manager._polishing_pass(
        ep_num=1,
        draft_content="これは初稿です。",
        gen_ctx=gen_ctx,
        temp=0.7,
        reporter=MagicMock()
    )

    # Should fallback to draft_content since the polished version was too short (below ratio)
    assert polished == "これは初稿です。"
