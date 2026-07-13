"""
tests/test_entertainment_loop_persistence.py
src/backend/entertainment_loop.py のDB保存処理の統合テスト。
"""
from unittest.mock import AsyncMock

import pytest

from src.backend.entertainment_loop import run_entertainment_first_loop
from src.models.entertainment_check import EntertainmentCheckResult


class DummyChecker:
    def __init__(self, result):
        self.result = result
        self.call_count = 0

    async def check(self, rough_plot, opening_chars):
        self.call_count += 1
        return self.result


class TestEntertainmentLoopPersistence:
    @pytest.mark.asyncio
    async def test_save_on_pass(self):
        checker = DummyChecker(EntertainmentCheckResult(
            interest_score=80,
            physiological_reaction="カタルシス",
            would_continue_reading=True,
            feedback="良い",
        ))
        repo = AsyncMock()
        result = await run_entertainment_first_loop(
            checker, "plot", "opening",
            repo=repo, book_id=1, ep_num=1,
        )
        assert result.interest_score == 80
        repo.save_entertainment_check_log.assert_called_once()
        call_kwargs = repo.save_entertainment_check_log.call_args.kwargs
        assert call_kwargs["book_id"] == 1
        assert call_kwargs["ep_num"] == 1
        assert call_kwargs["interest_score"] == 80

    @pytest.mark.asyncio
    async def test_save_on_fail(self):
        checker = DummyChecker(EntertainmentCheckResult(
            interest_score=40,
            physiological_reaction="無反応",
            would_continue_reading=False,
            feedback="bad",
        ))
        repo = AsyncMock()
        result = await run_entertainment_first_loop(
            checker, "plot", "opening",
            max_retries=0,
            repo=repo, book_id=1, ep_num=1,
        )
        assert result.interest_score == 40
        repo.save_entertainment_check_log.assert_called_once()
