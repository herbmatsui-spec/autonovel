"""
tests/test_entertainment_loop.py
src/backend/entertainment_loop.py の単体テスト。
"""
from unittest.mock import AsyncMock

import pytest

from src.backend.entertainment_loop import (
    DEFAULT_ENTERTAINMENT_THRESHOLD,
    DEFAULT_MAX_RETRIES,
    run_entertainment_first_loop,
)
from src.models.entertainment_check import EntertainmentCheckResult


class DummyChecker:
    def __init__(self, results):
        self.results = results
        self.call_count = 0

    async def check(self, rough_plot, opening_chars):
        idx = min(self.call_count, len(self.results) - 1)
        self.call_count += 1
        return self.results[idx]


class TestRunEntertainmentFirstLoop:
    @pytest.mark.asyncio
    async def test_pass_on_first_attempt(self):
        checker = DummyChecker(results=[
            EntertainmentCheckResult(interest_score=85, physiological_reaction="カタルシス", would_continue_reading=True, feedback="良い"),
        ])
        result = await run_entertainment_first_loop(checker, "plot", "opening")
        assert result.interest_score == 85
        assert checker.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_and_pass(self):
        checker = DummyChecker(results=[
            EntertainmentCheckResult(interest_score=40, physiological_reaction="無反応", would_continue_reading=False, feedback="つまらない"),
            EntertainmentCheckResult(interest_score=80, physiological_reaction="背筋", would_continue_reading=True, feedback="良い"),
        ])
        regenerate = AsyncMock(return_value="new plot")
        result = await run_entertainment_first_loop(checker, "plot", "opening", max_retries=2, regenerate_callback=regenerate)
        assert result.interest_score == 80
        assert checker.call_count == 2
        assert regenerate.call_count == 1

    @pytest.mark.asyncio
    async def test_fail_after_max_retries(self):
        checker = DummyChecker(results=[
            EntertainmentCheckResult(interest_score=40, physiological_reaction="無反応", would_continue_reading=False, feedback="つまらない"),
            EntertainmentCheckResult(interest_score=40, physiological_reaction="無反応", would_continue_reading=False, feedback="still bad"),
            EntertainmentCheckResult(interest_score=40, physiological_reaction="無反応", would_continue_reading=False, feedback="still bad"),
        ])
        result = await run_entertainment_first_loop(checker, "plot", "opening", max_retries=2)
        assert result.interest_score == 40
        assert checker.call_count == 1

    @pytest.mark.asyncio
    async def test_regenerate_exception_stops_loop(self):
        checker = DummyChecker(results=[
            EntertainmentCheckResult(interest_score=40, physiological_reaction="無反応", would_continue_reading=False, feedback="bad"),
            EntertainmentCheckResult(interest_score=40, physiological_reaction="無反応", would_continue_reading=False, feedback="bad"),
        ])
        regenerate = AsyncMock(side_effect=RuntimeError("regen failed"))
        result = await run_entertainment_first_loop(checker, "plot", "opening", max_retries=2, regenerate_callback=regenerate)
        assert result.interest_score == 40
        assert regenerate.call_count == 1
