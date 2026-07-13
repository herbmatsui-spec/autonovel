"""
tests/test_early_entertainment_checker.py
src/agents/early_entertainment_checker.py の単体テスト。
"""
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.early_entertainment_checker import EarlyEntertainmentChecker
from src.models.entertainment_check import EntertainmentCheckResult


class TestEarlyEntertainmentChecker:
    def test_none_prompt_manager_returns_fallback(self):
        checker = EarlyEntertainmentChecker(llm=MagicMock(), prompt_manager=None)
        import asyncio
        result = asyncio.run(checker.check("plot", "opening"))
        assert result.interest_score == 0
        assert result.would_continue_reading is False

    def test_valid_llm_response(self):
        llm = MagicMock()
        llm.generate_json = AsyncMock(return_value={
            "success": True,
            "metadata": {
                "interest_score": 85,
                "physiological_reaction": "背筋の寒さ",
                "would_continue_reading": True,
                "feedback": "展開が読めない",
            }
        })
        pm = MagicMock()
        pm.build_early_entertainment_check_prompt = AsyncMock(return_value="prompt")
        checker = EarlyEntertainmentChecker(llm=llm, prompt_manager=pm)
        import asyncio
        result = asyncio.run(checker.check("plot", "opening"))
        assert result.interest_score == 85
        assert result.physiological_reaction == "背筋の寒さ"
        assert result.would_continue_reading is True

    def test_invalid_score_clamped_to_zero(self):
        llm = MagicMock()
        llm.generate_json = AsyncMock(return_value={
            "success": True,
            "metadata": {
                "interest_score": 150,
                "physiological_reaction": "テスト",
                "would_continue_reading": True,
                "feedback": "テスト",
            }
        })
        pm = MagicMock()
        pm.build_early_entertainment_check_prompt = AsyncMock(return_value="prompt")
        checker = EarlyEntertainmentChecker(llm=llm, prompt_manager=pm)
        import asyncio
        result = asyncio.run(checker.check("plot", "opening"))
        assert result.interest_score == 0

    def test_llm_exception_returns_fallback(self):
        llm = AsyncMock(side_effect=RuntimeError("LLM error"))
        pm = MagicMock()
        pm.build_early_entertainment_check_prompt = AsyncMock(return_value="prompt")
        checker = EarlyEntertainmentChecker(llm=llm, prompt_manager=pm)
        import asyncio
        result = asyncio.run(checker.check("plot", "opening"))
        assert result.interest_score == 0
        assert result.feedback == "検証失敗"
