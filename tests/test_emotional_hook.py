"""
tests/test_emotional_hook.py
src/models/emotional_hook.py の単体テスト。
"""
import logging

import pytest
from pydantic import ValidationError

from src.models.emotional_hook import EmotionalHookSpec


class TestEmotionalHookSpec:
    def test_valid_catharsis(self):
        hook = EmotionalHookSpec(
            hook_name="catharsis",
            one_line_intent="長い苦悩の末に訪れる解放",
            target_tension_peak=85,
        )
        assert hook.hook_name == "catharsis"
        assert hook.target_tension_peak == 85
        assert hook.subordinate_to_quality is True

    def test_one_line_intent_max_length(self):
        long_intent = "a" * 121
        with pytest.raises(ValidationError):
            EmotionalHookSpec(
                hook_name="catharsis",
                one_line_intent=long_intent,
            )

    def test_one_line_intent_120_chars_ok(self):
        intent = "a" * 120
        hook = EmotionalHookSpec(
            hook_name="catharsis",
            one_line_intent=intent,
        )
        assert len(hook.one_line_intent) == 120

    def test_unknown_hook_raises_validation_error(self):
        with pytest.raises(ValidationError):
            EmotionalHookSpec(
                hook_name="unknown_hook",
                one_line_intent="テスト",
            )

    def test_empty_hook_name_raises_validation_error(self):
        with pytest.raises(ValidationError):
            EmotionalHookSpec(
                hook_name="",
                one_line_intent="テスト",
            )

    def test_subordinate_false_logs_warning(self, caplog):
        with caplog.at_level(logging.WARNING):
            EmotionalHookSpec(
                hook_name="catharsis",
                one_line_intent="テスト",
                subordinate_to_quality=False,
            )
        assert "subordinate_to_quality=False" in caplog.text

    def test_target_tension_peak_range(self):
        with pytest.raises(ValidationError):
            EmotionalHookSpec(
                hook_name="catharsis",
                one_line_intent="テスト",
                target_tension_peak=101,
            )
        with pytest.raises(ValidationError):
            EmotionalHookSpec(
                hook_name="catharsis",
                one_line_intent="テスト",
                target_tension_peak=-1,
            )
