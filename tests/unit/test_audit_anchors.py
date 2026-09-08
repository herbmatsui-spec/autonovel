"""Unit tests for Audit Anchor Examples and Presets (Pillar 4 / Checkpoint 1: Steps 1-6)."""

import pytest

from src.agents.specialists.anchors import (
    SPECIALIST_ANCHOR_PRESETS,
    AuditAnchorExample,
    AnchorPreset,
    get_anchor_preset,
)


EXPECTED_SPECIALISTS = [
    "reader_hook",
    "consistency",
    "structure",
    "emotion_curve",
    "style",
    "factual",
    "creativity",
    "multimodal",
]


def test_all_specialist_presets_registered():
    """Verify that all 8 specialists have registered anchor presets."""
    for name in EXPECTED_SPECIALISTS:
        preset = get_anchor_preset(name)
        assert preset is not None, f"Anchor preset for {name} is missing"
        assert preset.specialist_name == name


def test_anchor_preset_tiers_and_scores():
    """Verify that each specialist has high, mid, low anchors with monotonic scores."""
    for name in EXPECTED_SPECIALISTS:
        preset = get_anchor_preset(name)
        assert preset is not None
        assert len(preset.anchors) == 3, f"{name} must have exactly 3 tier anchors"

        high = preset.get_by_tier("high")
        mid = preset.get_by_tier("mid")
        low = preset.get_by_tier("low")

        assert high is not None, f"{name} missing high tier"
        assert mid is not None, f"{name} missing mid tier"
        assert low is not None, f"{name} missing low tier"

        assert high.score >= 80.0, f"{name} high tier score {high.score} < 80"
        assert 55.0 <= mid.score <= 75.0, f"{name} mid tier score {mid.score} not in [55, 75]"
        assert low.score <= 50.0, f"{name} low tier score {low.score} > 50"

        # Key features and critique must not be empty
        for anchor in (high, mid, low):
            assert len(anchor.sample_text.strip()) > 0
            assert len(anchor.critique.strip()) > 0
            assert len(anchor.key_features) > 0


def test_anchor_format_for_prompt():
    """Verify format_for_prompt outputs readable markdown text."""
    preset = get_anchor_preset("reader_hook")
    assert preset is not None
    prompt_text = preset.format_for_prompt()

    assert "### 【採点基準アンカー例（reader_hook）】" in prompt_text
    assert "HIGH水準" in prompt_text
    assert "MID水準" in prompt_text
    assert "LOW水準" in prompt_text
    assert "逃げろ、アレン！" in prompt_text
