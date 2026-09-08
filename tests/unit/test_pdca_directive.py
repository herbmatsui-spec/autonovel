"""Unit tests for PDCADirectiveGenerator (Part 4 / Step 42 / Checkpoint 7)."""

import pytest
from src.agents.specialist_auditor_base import ActionableDiff
from src.services.pdca_directive import (
    WritingDirective,
    PDCACycleResult,
    PDCADirectiveGenerator,
    DIMENSION_PROMPT_TEMPLATES,
)


def test_writing_directive_formatting():
    """Verify WritingDirective structure and prompt formatting."""
    d = WritingDirective(
        dimension="structure",
        severity="CRITICAL",
        target_location="起（導入部）",
        current_issue="主人公の日常が2000字続き事件が起きない",
        mandatory_instruction="500字以内に異常事態を発生させ、主人公の動機を明確に提示すること。",
        rationale="導入部の離脱を防ぎ、商業出版水準の牽引力を確保するため。",
    )
    assert d.severity == "CRITICAL"
    text = d.format_for_prompt()
    assert "【最優先必須修正】" in text
    assert "起（導入部）" in text
    assert "500字以内に異常事態" in text


def test_identify_target_dimensions():
    """Verify lowest scoring dimensions below threshold are correctly identified."""
    scores = {
        "structure": 85.0,
        "consistency": 45.0,  # lowest
        "emotion_curve": 62.0,  # 2nd lowest
        "style": 88.0,
    }
    targets = PDCADirectiveGenerator.identify_target_dimensions(scores, target_threshold=75.0, top_k=2)
    assert len(targets) == 2
    assert targets[0][0] == "consistency"
    assert targets[0][1] == 45.0
    assert targets[1][0] == "emotion_curve"
    assert targets[1][1] == 62.0


def test_diff_to_directive_severity_mapping():
    """Verify severity mapping from dimension scores."""
    diff = ActionableDiff(
        location="結末",
        original_quote="彼は眠った。",
        improved_suggestion="未来への希望を胸に抱き、深い安堵とともに目を閉じた。",
        rationale="カタルシス強化",
    )

    # Score < 50 -> CRITICAL
    d_crit = PDCADirectiveGenerator.diff_to_directive(diff, "emotion_curve", dimension_score=42.0)
    assert d_crit.severity == "CRITICAL"

    # Score 65 -> MAJOR
    d_maj = PDCADirectiveGenerator.diff_to_directive(diff, "emotion_curve", dimension_score=65.0)
    assert d_maj.severity == "MAJOR"

    # Score 80 -> MINOR
    d_min = PDCADirectiveGenerator.diff_to_directive(diff, "emotion_curve", dimension_score=80.0)
    assert d_min.severity == "MINOR"


def test_generate_directives_and_prioritization():
    """Verify generation combines diffs and templates, sorted by severity."""
    scores = {
        "structure": 48.0,  # CRITICAL
        "reader_hook": 65.0,  # MAJOR
        "style": 85.0,
    }
    diff = ActionableDiff(
        location="reader_hook 冒頭",
        original_quote="朝だった。",
        improved_suggestion="雷鳴が轟いた。",
        rationale="読者フック向上",
    )

    directives = PDCADirectiveGenerator.generate_directives_for_regeneration(
        scores_by_specialist=scores,
        actionable_diffs=[diff],
        target_threshold=75.0,
    )

    assert len(directives) >= 2
    # First should be CRITICAL (structure)
    assert directives[0].severity == "CRITICAL"
    assert directives[0].dimension == "structure"
    # Second should be MAJOR (reader_hook)
    assert directives[1].severity == "MAJOR"


def test_format_directives_for_llm_prompt():
    """Verify formatted output produces structured prompt instructions."""
    d1 = WritingDirective(
        dimension="consistency",
        severity="CRITICAL",
        target_location="第1章",
        current_issue="死亡キャラ登場",
        mandatory_instruction="故人としての回想に変更",
        rationale="論理破綻解消",
    )
    prompt_block = PDCADirectiveGenerator.format_directives_for_llm_prompt([d1])
    assert "【閉ループPDCA・再生成必須制約（必ず遵守すること）】" in prompt_block
    assert "《修正指示 1》" in prompt_block
    assert "故人としての回想に変更" in prompt_block
