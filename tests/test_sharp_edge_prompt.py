"""
tests/test_sharp_edge_prompt.py
prompts/manager.py の build_sharp_edge_proposal_prompt の単体テスト。
"""
import pytest

from prompts.manager import PromptManager


class DummyPromptManager(PromptManager):
    def __init__(self):
        pass  # skip registry init


class TestSharpEdgeProposalPrompt:
    def setup_method(self):
        self.pm = DummyPromptManager()

    def test_contains_three_edge_types(self):
        import asyncio
        result = asyncio.run(self.pm.build_sharp_edge_proposal_prompt("テストプロット概要"))
        assert "ending_pullback" in result
        assert "protagonist_flaw" in result
        assert "abnormal_dialogue" in result

    def test_plot_summary_is_embedded(self):
        import asyncio
        summary = "主人公が復讐する話"
        result = asyncio.run(self.pm.build_sharp_edge_proposal_prompt(summary))
        assert summary in result

    def test_json_array_requirement_present(self):
        import asyncio
        result = asyncio.run(self.pm.build_sharp_edge_proposal_prompt("テスト"))
        assert "JSON配列" in result or "JSON" in result
