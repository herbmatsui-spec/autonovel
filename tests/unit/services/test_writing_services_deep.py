"""src/services/writing_services.py の深層単体テスト."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.db import BookDbModel, PlotDbModel
from src.models.writing import WritingContext
from src.services.writing_services import (
    GenerationLoopManager,
    WritingGenerationContext,
    clean_writing_response,
)


# ==============================================================================
# 1. clean_writing_response & WritingGenerationContext Tests
# ==============================================================================


def test_clean_writing_response_variations():
    # Multiple thinking tags
    raw = "<thinking>plan 1</thinking>Hello <thinking>plan 2</thinking>World!"
    assert clean_writing_response(raw) == "Hello World!"

    # Multiline thinking
    raw_multiline = """<thinking>
    Step 1: think
    Step 2: write
    </thinking>This is pure content."""
    assert clean_writing_response(raw_multiline) == "This is pure content."

    # No thinking tag
    assert clean_writing_response("Plain text.") == "Plain text."


def test_writing_generation_context_build_sys_inst():
    ctx = WritingGenerationContext(
        sys_inst="Base instruction.",
        pov_instruction="First person POV.",
        feedback_patch="Fix dialogue rhythm.",
    )
    res = ctx.build_sys_inst()
    assert "Base instruction." in res
    assert "First person POV." in res
    assert "【🚨自己評価フィードバックパッチ】" in res
    assert "Fix dialogue rhythm." in res


def test_writing_generation_context_build_fw_prompt():
    ctx = WritingGenerationContext(
        fw_prompt="Write scene 1.",
        pov_instruction="POV details.",
        expanded_beats="Beat 1: Look at door.\nBeat 2: Enter room.",
    )
    res = ctx.build_fw_prompt(suffix="Do it quickly.")
    assert "Write scene 1." in res
    assert "POV details." in res
    assert "【📝 物理動作ビート分解（絶対遵守）】" in res
    assert "Beat 1: Look at door." in res
    assert "Do it quickly." in res


# ==============================================================================
# 2. GenerationLoopManager Helpers Tests
# ==============================================================================


@pytest.fixture
def manager_setup():
    repo = MagicMock()
    repo.session = MagicMock()
    llm = MagicMock()
    llm.generate_text = AsyncMock()
    llm.generate_json = AsyncMock()
    pm = MagicMock()
    critique = MagicMock()
    narrative = MagicMock()
    narrative.get_integrity_threshold.return_value = 0.8
    config = MagicMock()

    manager = GenerationLoopManager(
        repo=repo,
        llm=llm,
        pm=pm,
        critique=critique,
        narrative=narrative,
        config=config,
    )
    return manager, repo, llm, pm, narrative


def test_determine_pov_instruction(manager_setup):
    manager, _, _, _, _ = manager_setup
    reporter = MagicMock()

    # Catharsis -> POV change instruction
    res1 = manager._determine_pov_instruction(1, 50, True, reporter)
    assert "特殊割り込み指令" in res1

    # High tension (>= 80) -> POV change instruction
    res2 = manager._determine_pov_instruction(2, 85, False, reporter)
    assert "特殊割り込み指令" in res2

    # Normal tension (< 80) and not catharsis -> empty string
    res3 = manager._determine_pov_instruction(3, 40, False, reporter)
    assert res3 == ""


def test_calculate_ncs_score(manager_setup):
    manager, _, _, _, _ = manager_setup
    plot = PlotDbModel(
        id=1,
        book_id=1,
        ep_num=1,
        title="Ep 1",
        summary="伏線が回収される決戦の時",
        detailed_blueprint="クライマックスへ突入",
    )
    plot.is_catharsis = True
    ctx = WritingContext(
        book=BookDbModel(id=1, title="Test", genre="fantasy", target_eps=50),
        plot=plot,
        current_tension=85,
    )
    score = manager._calculate_ncs_score(1, ctx)
    # Catharsis (+50) + keyword '伏線' (+30) + ep_num <= 3 (+30) = 110
    assert score >= 80


@pytest.mark.asyncio
async def test_phase_prepare_context_with_json_style_dna(manager_setup):
    manager, _, _, _, _ = manager_setup
    book = BookDbModel(id=1, title="Test", genre="fantasy")
    book.style_dna = json.dumps({"mode": "style_light_novel"})
    ctx = WritingContext(
        book=book,
        plot=PlotDbModel(id=1, book_id=1, ep_num=1, title="Ep 1"),
        current_tension=50,
        target_word_count=3000,
        prose_samples=["Sample prose."],
    )
    gen_ctx, should_dogfeed, should_heavy_audit, should_beat_decompose, ncs_score = (
        await manager._phase_prepare_context(
            ep_num=1,
            ctx=ctx,
            sys_inst="System inst",
            fw_prompt="Prompt",
            is_easy_mode=False,
            reporter=None,
        )
    )
    assert gen_ctx.style_key == "style_light_novel"
    assert gen_ctx.target_word_count == 3000
    assert gen_ctx.prose_sample == "Sample prose."
    assert isinstance(ncs_score, int)


@pytest.mark.asyncio
async def test_surgical_causality_healing_pass(manager_setup):
    manager, _, llm, pm, _ = manager_setup
    pm.build_surgical_causality_healing_prompt.return_value = "healer prompt"
    
    mock_res = MagicMock()
    mock_res.success = True
    mock_res.story_content = "Line 1\nLine 2 healed\nLine 3"
    llm.generate_text.return_value = mock_res

    content = "Line 1\nLine 2 broken\nLine 3"
    result = await manager.surgical_causality_healing_pass(
        content=content,
        world_settings="World rules",
        blueprint="Blueprint",
        failure_reason="broken event",
        snippets=["broken"],
    )
    assert "Line 2 healed" in result or result == mock_res.story_content


@pytest.mark.asyncio
async def test_expand_scene_beats(manager_setup):
    manager, _, llm, pm, _ = manager_setup
    pm.build_beat_expansion_prompt.return_value = "expansion prompt"
    
    mock_res = MagicMock()
    mock_res.unwrap_or.return_value = (
        {"beats": [{"beat_num": 1, "physical_action": "Draw blade", "sensory_tags": ["sharp"], "emotion_phase": "focus", "word_budget": 200}]},
        "",
    )
    llm.generate_json.return_value = mock_res

    beats = await manager._expand_scene_beats(1, "blueprint", 0.7, None)
    assert "Draw blade" in beats


@pytest.mark.asyncio
async def test_draft_episode_parts(manager_setup):
    manager, _, llm, _, _ = manager_setup
    gen_ctx = WritingGenerationContext(
        sys_inst="System instruction",
        fw_prompt="Prompt",
        style_key="standard",
    )
    mock_res = MagicMock()
    mock_res.success = True
    mock_res.story_content = "Drafted scene content." * 10
    llm.generate_text.return_value = mock_res

    content = await manager._draft_episode_parts(1, gen_ctx, 0.7, None)
    assert "Drafted scene content." in content


@pytest.mark.asyncio
async def test_polishing_pass(manager_setup):
    manager, _, llm, pm, _ = manager_setup
    pm.build_polishing_prompt.return_value = "polishing prompt"
    mock_res = MagicMock()
    mock_res.success = True
    mock_res.story_content = "Polished scene content."
    llm.generate_text.return_value = mock_res

    gen_ctx = WritingGenerationContext(enable_polishing=True)
    polished = await manager._polishing_pass(1, "Raw text", gen_ctx, 0.7, None)
    assert polished == "Polished scene content."


@pytest.mark.asyncio
async def test_extract_episode_metadata(manager_setup):
    manager, _, llm, pm, _ = manager_setup
    pm.build_metadata_extraction_prompt.return_value = "meta prompt"
    mock_res = MagicMock()
    mock_res.success = True
    mock_res.metadata = {"characters": ["Hero"], "summary": "An adventure begins."}
    llm.generate_json.return_value = mock_res

    meta = await manager._extract_episode_metadata(1, "Story text", "blueprint", 0.7)
    assert meta["summary"] == "An adventure begins."


@pytest.mark.asyncio
async def test_execute_generation_loop_easy_mode(manager_setup):
    manager, _, llm, _, _ = manager_setup
    ctx = WritingContext(
        book=BookDbModel(id=1, title="Hero Journey", genre="fantasy"),
        plot=PlotDbModel(id=1, book_id=1, ep_num=1, title="Chapter 1"),
        current_tension=50,
    )
    # Mock draft returning content
    manager._phase_drafting = AsyncMock(return_value=("Scene content", {"summary": "Done"}))
    manager._phase_audit = AsyncMock(return_value=(True, 0.95, True, "", []))
    manager._run_dogfeeding_loop = AsyncMock(return_value=True)

    final_content, final_meta, is_integrity_ok = await manager.execute_generation_loop(
        ep_num=1,
        ctx=ctx,
        sys_inst="Sys",
        fw_prompt="Fw",
        passion=0.8,
        is_easy_mode=True,
        reporter=None,
    )
    assert final_content == "Scene content"
    assert is_integrity_ok is True
