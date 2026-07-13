"""
tests/test_state_desires_to_hook.py
streamlit_app/state.py の desires_to_hook の単体テスト。
"""
import pytest

from streamlit_app.state import DESIRE_TO_HOOK_MAP, desires_to_hook


class TestDesiresToHook:
    def test_catharsis_maps_to_catharsis(self):
        hook = desires_to_hook(["カタルシス"])
        assert hook is not None
        assert hook.hook_name == "catharsis"

    def test_empathy_peak_maps_correctly(self):
        hook = desires_to_hook(["共感の最深"])
        assert hook is not None
        assert hook.hook_name == "empathy_peak"

    def test_empty_desires_returns_none(self):
        assert desires_to_hook([]) is None

    def test_unknown_desire_returns_none(self):
        assert desires_to_hook(["不明な感情"]) is None

    def test_all_desire_map_keys_are_valid_hooks(self):
        from config.emotional_hook_vocabulary import validate_hook
        for desire, hook_name in DESIRE_TO_HOOK_MAP.items():
            assert validate_hook(hook_name), f"{desire} -> {hook_name} が不正です"
