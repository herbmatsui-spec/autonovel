"""
tests/test_entertainment_check_model.py
src/models/entertainment_check.py の単体テスト。
"""
import pytest
from pydantic import ValidationError

from src.models.entertainment_check import EntertainmentCheckResult


class TestEntertainmentCheckResult:
    def test_valid_result(self):
        result = EntertainmentCheckResult(
            interest_score=85,
            physiological_reaction="背筋の寒さ",
            would_continue_reading=True,
            feedback="展開が読めない",
        )
        assert result.interest_score == 85
        assert result.would_continue_reading is True

    def test_interest_score_boundary_0(self):
        result = EntertainmentCheckResult(
            interest_score=0,
            physiological_reaction="無反応",
            would_continue_reading=False,
            feedback="つまらない",
        )
        assert result.interest_score == 0

    def test_interest_score_boundary_100(self):
        result = EntertainmentCheckResult(
            interest_score=100,
            physiological_reaction="カタルシス",
            would_continue_reading=True,
            feedback="傑作",
        )
        assert result.interest_score == 100

    def test_interest_score_over_100_raises(self):
        with pytest.raises(ValidationError):
            EntertainmentCheckResult(
                interest_score=101,
                physiological_reaction="テスト",
                would_continue_reading=True,
                feedback="テスト",
            )

    def test_interest_score_under_0_raises(self):
        with pytest.raises(ValidationError):
            EntertainmentCheckResult(
                interest_score=-1,
                physiological_reaction="テスト",
                would_continue_reading=True,
                feedback="テスト",
            )

    def test_feedback_max_length(self):
        long_feedback = "a" * 301
        with pytest.raises(ValidationError):
            EntertainmentCheckResult(
                interest_score=50,
                physiological_reaction="テスト",
                would_continue_reading=True,
                feedback=long_feedback,
            )
