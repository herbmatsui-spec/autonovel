"""
tests/test_emotional_hook_vocabulary.py
config/emotional_hook_vocabulary.py の単体テスト。
"""
import pytest

from config.emotional_hook_vocabulary import (
    EMOTIONAL_HOOKS,
    get_hook_peak_tension,
    validate_hook,
)


class TestEmotionalHookVocabulary:
    def test_known_hook_returns_correct_peak_tension(self):
        assert get_hook_peak_tension("catharsis") == 85
        assert get_hook_peak_tension("chilling") == 90
        assert get_hook_peak_tension("serenity") == 40

    def test_unknown_hook_returns_fallback(self):
        assert get_hook_peak_tension("unknown_hook") == 50
        assert get_hook_peak_tension("") == 50

    def test_validate_hook_known(self):
        assert validate_hook("catharsis") is True
        assert validate_hook("empathy_peak") is True

    def test_validate_hook_unknown(self):
        assert validate_hook("not_exist") is False
        assert validate_hook("") is False

    def test_all_hook_names_are_non_empty(self):
        for hook_name in EMOTIONAL_HOOKS:
            assert len(hook_name) > 0

    def test_all_entries_have_three_elements(self):
        for hook_name, entry in EMOTIONAL_HOOKS.items():
            assert len(entry) == 3, f"{hook_name}のエントリが3要素ではありません"

    def test_all_peak_values_in_range(self):
        for hook_name, entry in EMOTIONAL_HOOKS.items():
            _, _, peak = entry
            assert 0 <= peak <= 100, f"{hook_name}のtension値が範囲外です: {peak}"
