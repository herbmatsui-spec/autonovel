"""
tests/test_early_entertainment_prompt.py
prompts/manager.py の build_early_entertainment_check_prompt の単体テスト。
"""
import pytest

from prompts.manager import PromptManager


class DummyPromptManager(PromptManager):
    def __init__(self):
        pass


class TestEarlyEntertainmentPrompt:
    def setup_method(self):
        self.pm = DummyPromptManager()

    def test_contains_quality_ignore_instruction(self):
        import asyncio
        result = asyncio.run(self.pm.build_early_entertainment_check_prompt(
            rough_plot="テストプロット",
            opening_500_chars="テスト冒頭",
        ))
        assert "品質を評価せず" in result or "品質を一切評価せず" in result
        assert "面白さのみ" in result

    def test_inputs_embedded(self):
        import asyncio
        rough = "プロット内容"
        opening = "冒頭500字の内容"
        result = asyncio.run(self.pm.build_early_entertainment_check_prompt(
            rough_plot=rough,
            opening_500_chars=opening,
        ))
        assert rough in result
        assert opening in result

    def test_opening_truncated_to_500_chars(self):
        import asyncio
        long_opening = "a" * 600
        result = asyncio.run(self.pm.build_early_entertainment_check_prompt(
            rough_plot="p",
            opening_500_chars=long_opening,
        ))
        assert "a" * 500 in result
        assert "a" * 501 not in result
