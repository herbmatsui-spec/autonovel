"""Unit tests for WritingGenerationContext in src/backend/writing_service.py."""
from unittest.mock import MagicMock, patch
from src.backend.writing_service import WritingGenerationContext


def test_writing_generation_context_defaults():
    """Test WritingGenerationContext default values."""
    ctx = WritingGenerationContext()
    assert ctx.style_key == "style_web_standard"
    assert ctx.target_word_count == 2000
    assert ctx.enable_polishing is True
    assert ctx.prose_sample == ""
    assert ctx.plot is None
    assert ctx.sys_inst == ""
    assert ctx.fw_prompt == ""
    assert ctx.pov_instruction == ""
    assert ctx.expanded_beats == ""
    assert ctx.feedback_patch == ""


def test_writing_generation_context_with_values():
    """Test WritingGenerationContext with custom values."""
    ctx = WritingGenerationContext(
        sys_inst="Base instruction",
        fw_prompt="Base prompt",
        pov_instruction="POV instruction",
        expanded_beats="Beat 1\nBeat 2",
        feedback_patch="Feedback patch",
        style_key="custom_style",
        target_word_count=1500,
        enable_polishing=False,
        prose_sample="Sample prose",
        plot={"key": "value"}
    )

    assert ctx.sys_inst == "Base instruction"
    assert ctx.fw_prompt == "Base prompt"
    assert ctx.pov_instruction == "POV instruction"
    assert ctx.expanded_beats == "Beat 1\nBeat 2"
    assert ctx.feedback_patch == "Feedback patch"
    assert ctx.style_key == "custom_style"
    assert ctx.target_word_count == 1500
    assert ctx.enable_polishing is False
    assert ctx.prose_sample == "Sample prose"
    assert ctx.plot == {"key": "value"}


def test_writing_generation_context_build_sys_inst_with_all_fields():
    """Test sys_inst building with all fields."""
    ctx = WritingGenerationContext(
        sys_inst="Base instruction",
        pov_instruction="POV instruction",
        feedback_patch="Feedback patch",
    )
    result = ctx.build_sys_inst()
    assert "Base instruction" in result
    assert "POV instruction" in result
    assert "【🚨自己評価フィードバックパッチ】" in result
    assert "Feedback patch" in result


def test_writing_generation_context_build_sys_inst_minimal():
    """Test sys_inst with only base instruction."""
    ctx = WritingGenerationContext(sys_inst="Only base")
    assert ctx.build_sys_inst() == "Only base"


def test_writing_generation_context_build_sys_inst_no_feedback():
    """Test sys_inst without feedback patch."""
    ctx = WritingGenerationContext(
        sys_inst="Base",
        pov_instruction="POV",
    )
    result = ctx.build_sys_inst()
    assert "Base" in result
    assert "POV" in result
    assert "自己評価フィードバックパッチ" not in result


def test_writing_generation_context_build_fw_prompt_with_all_fields():
    """Test fw_prompt building with all fields."""
    ctx = WritingGenerationContext(
        fw_prompt="Base prompt",
        pov_instruction="POV instruction",
        expanded_beats="Beat 1\nBeat 2",
    )
    result = ctx.build_fw_prompt("Suffix text")
    assert "Base prompt" in result
    assert "POV instruction" in result
    assert "物理動作ビート分解" in result
    assert "Beat 1" in result
    assert "Beat 2" in result
    assert "Suffix text" in result


def test_writing_generation_context_build_fw_prompt_minimal():
    """Test fw_prompt with minimal fields."""
    ctx = WritingGenerationContext(fw_prompt="Only prompt")
    result = ctx.build_fw_prompt()
    assert result == "Only prompt"


def test_writing_generation_context_build_fw_prompt_no_beats():
    """Test fw_prompt without expanded beats."""
    ctx = WritingGenerationContext(
        fw_prompt="Base",
        pov_instruction="POV",
    )
    result = ctx.build_fw_prompt()
    assert "物理動作ビート分解" not in result


def test_writing_service_audit_generated_text():
    """Test WritingService.audit_generated_text executes UnifiedAuditor quantitative analysis."""
    from src.backend.writing_service import WritingService

    service = WritingService(writer=MagicMock())
    sample_text = "「行くぞ！」アルトは叫び、剣を抜いた。夜の風が冷たく吹き抜ける。"
    result = service.audit_generated_text(sample_text)

    assert "quantitative_score" in result
    assert "is_acceptable" in result
    assert "warnings" in result
    assert isinstance(result["warnings"], list)
    assert result["quantitative_score"] > 0


