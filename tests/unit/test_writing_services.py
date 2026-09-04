"""Unit tests for src/services/writing_services.py - Writing generation services."""
import pytest
from unittest.mock import MagicMock, patch

# Test WritingGenerationContext (continued from previous)
def test_writing_generation_context_defaults():
    """Test WritingGenerationContext default values."""
    from src.services.writing_services import WritingGenerationContext
    
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
    from src.services.writing_services import WritingGenerationContext
    
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
    from src.services.writing_services import WritingGenerationContext
    
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
    from src.services.writing_services import WritingGenerationContext
    
    ctx = WritingGenerationContext(sys_inst="Only base")
    assert ctx.build_sys_inst() == "Only base"

def test_writing_generation_context_build_sys_inst_no_feedback():
    """Test sys_inst without feedback patch."""
    from src.services.writing_services import WritingGenerationContext
    
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
    from src.services.writing_services import WritingGenerationContext
    
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
    from src.services.writing_services import WritingGenerationContext
    
    ctx = WritingGenerationContext(fw_prompt="Only prompt")
    result = ctx.build_fw_prompt()
    assert result == "Only prompt"

def test_writing_generation_context_build_fw_prompt_no_beats():
    """Test fw_prompt without expanded beats."""
    from src.services.writing_services import WritingGenerationContext
    
    ctx = WritingGenerationContext(
        fw_prompt="Base",
        pov_instruction="POV",
    )
    result = ctx.build_fw_prompt()
    assert "物理動作ビート分解" not in result

# Test GenerationLoopManager initialization and helper methods
def test_generation_loop_manager_init():
    """Test GenerationLoopManager initialization."""
    from src.services.writing_services import GenerationLoopManager
    
    mock_repo = MagicMock()
    mock_llm = MagicMock()
    mock_pm = MagicMock()
    mock_critique = MagicMock()
    mock_narrative = MagicMock()
    mock_config = MagicMock()
    
    manager = GenerationLoopManager(
        repo=mock_repo,
        llm=mock_llm,
        pm=mock_pm,
        critique=mock_critique,
        narrative=mock_narrative,
        config=mock_config,
    )
    
    assert manager.repo == mock_repo
    assert manager.llm == mock_llm
    assert manager.pm == mock_pm
    assert manager.critique == mock_critique
    assert manager.narrative == mock_narrative
    assert manager.config == mock_config

def test_generation_loop_manager_determine_pov_instruction_high_tension():
    """Test _determine_pov_instruction for high tension."""
    from src.services.writing_services import GenerationLoopManager
    
    manager = GenerationLoopManager(None, None, None, None, None, None)
    mock_reporter = MagicMock()
    
    result = manager._determine_pov_instruction(1, 85, False, mock_reporter)
    
    assert "幕間・視点変更" in result
    assert "敵役の絶望" in result or "ヒロイン" in result
    mock_reporter.report.assert_called()

def test_generation_loop_manager_determine_pov_instruction_catharsis():
    """Test _determine_pov_instruction for catharsis episode."""
    from src.services.writing_services import GenerationLoopManager
    
    manager = GenerationLoopManager(None, None, None, None, None, None)
    mock_reporter = MagicMock()
    
    result = manager._determine_pov_instruction(1, 50, True, mock_reporter)
    
    assert "幕間・視点変更" in result
    mock_reporter.report.assert_called()

def test_generation_loop_manager_determine_pov_instruction_normal():
    """Test _determine_pov_instruction for normal episode."""
    from src.services.writing_services import GenerationLoopManager
    
    manager = GenerationLoopManager(None, None, None, None, None, None)
    mock_reporter = MagicMock()
    
    result = manager._determine_pov_instruction(1, 50, False, mock_reporter)
    
    assert result == ""

def test_generation_loop_manager_calculate_ncs_score():
    """Test _calculate_ncs_score."""
    from src.services.writing_services import GenerationLoopManager
    
    manager = GenerationLoopManager(None, None, None, None, None, None)
    mock_ctx = MagicMock()
    mock_ctx.plot = MagicMock()
    mock_ctx.plot.is_catharsis = True
    mock_ctx.plot.summary = "climax battle"
    mock_ctx.plot.detailed_blueprint = "resolution"
    mock_ctx.book = MagicMock()
    mock_ctx.book.target_eps = 10
    
    with patch("config.AUDIT_TRIGGER_KEYWORDS", ["climax", "battle"]):
        score = manager._calculate_ncs_score(1, mock_ctx)
    
    assert score >= 80  # 50 (catharsis) + 30 (keywords)

def test_generation_loop_manager_calculate_ncs_score_first_episode():
    """Test NCS score for first episode."""
    from src.services.writing_services import GenerationLoopManager
    
    manager = GenerationLoopManager(None, None, None, None, None, None)
    mock_ctx = MagicMock()
    mock_ctx.plot = MagicMock()
    mock_ctx.plot.is_catharsis = False
    mock_ctx.plot.summary = ""
    mock_ctx.plot.detailed_blueprint = ""
    mock_ctx.book = MagicMock()
    mock_ctx.book.target_eps = 50
    
    score = manager._calculate_ncs_score(1, mock_ctx)
    assert score >= 30  # first episode bonus

def test_generation_loop_manager_calculate_ncs_score_last_episodes():
    """Test NCS score for last episodes."""
    from src.services.writing_services import GenerationLoopManager
    
    manager = GenerationLoopManager(None, None, None, None, None, None)
    mock_ctx = MagicMock()
    mock_ctx.plot = MagicMock()
    mock_ctx.plot.is_catharsis = False
    mock_ctx.plot.summary = ""
    mock_ctx.plot.detailed_blueprint = ""
    mock_ctx.book = MagicMock()
    mock_ctx.book.target_eps = 10
    
    score = manager._calculate_ncs_score(9, mock_ctx)  # 9 out of 10
    assert score >= 30  # near end bonus