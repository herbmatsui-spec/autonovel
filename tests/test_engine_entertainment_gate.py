"""
tests/test_engine_entertainment_gate.py
src/backend/engine_plot.py の enforce_entertainment_gate 統合テスト。
"""
from unittest.mock import AsyncMock

import pytest

from src.backend.engine_plot import (
    ENFORCE_ENTERTAINMENT_FIRST,
    enforce_entertainment_gate,
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


class TestEnforceEntertainmentGate:
    def test_pass_returns_result(self):
        import asyncio
        checker = DummyChecker(results=[
            EntertainmentCheckResult(interest_score=80, physiological_reaction="カタルシス", would_continue_reading=True, feedback="良い"),
        ])
        result = asyncio.run(enforce_entertainment_gate(checker, "plot", "opening"))
        assert result.interest_score == 80

    def test_fail_raises_runtime_error(self):
        import asyncio
        checker = DummyChecker(results=[
            EntertainmentCheckResult(interest_score=40, physiological_reaction="無反応", would_continue_reading=False, feedback="bad"),
        ])
        with pytest.raises(RuntimeError, match="面白さ検証不合格"):
            asyncio.run(enforce_entertainment_gate(checker, "plot", "opening", max_retries=0))

    def test_disabled_enforcement_allows_fail(self, monkeypatch):
        import asyncio
        monkeypatch.setattr("src.backend.engine_plot.ENFORCE_ENTERTAINMENT_FIRST", False)
        checker = DummyChecker(results=[
            EntertainmentCheckResult(interest_score=40, physiological_reaction="無反応", would_continue_reading=False, feedback="bad"),
        ])
        result = asyncio.run(enforce_entertainment_gate(checker, "plot", "opening", max_retries=0))
        assert result.interest_score == 40
