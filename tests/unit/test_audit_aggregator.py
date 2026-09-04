"""Unit tests for AuditAggregator."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from src.services.audit_aggregator import (
    AuditAggregator, BookScoreResult, validate_weights, renormalize, SPECIALIST_NAMES
)
from src.agents.specialist_auditor_base import (
    SpecialistAuditor, SpecialistAuditResult, LLMUnavailableError
)


class FakeSpecialist(SpecialistAuditor):
    def __init__(self, name: str, score: float, should_fail: bool = False, degraded: bool = False):
        super().__init__(llm=None)
        self.specialist_name = name
        self._score = score
        self._should_fail = should_fail
        self._degraded = degraded

    async def audit(self, ctx):
        if self._should_fail:
            raise RuntimeError(f"{self.specialist_name} crashed")
        return SpecialistAuditResult(
            self.specialist_name,
            self._score,
            feedback={},
            suggestions=[],
            degraded=self._degraded,
        )


@pytest.fixture
def default_weights():
    return {n: 1.0 / len(SPECIALIST_NAMES) for n in SPECIALIST_NAMES}


class TestValidateWeights:
    def test_valid_default(self, default_weights):
        validate_weights(default_weights)

    def test_reject_bad_sum(self, default_weights):
        bad = {**default_weights, "consistency": 0.5}
        with pytest.raises(ValueError, match="sum to 1.0"):
            validate_weights(bad)

    def test_reject_missing_specialist(self, default_weights):
        incomplete = {k: v for k, v in default_weights.items() if k != "creativity"}
        with pytest.raises(ValueError, match="Missing weights"):
            validate_weights(incomplete)


class TestRenormalize:
    def test_partial_present(self, default_weights):
        rn = renormalize(default_weights, ["consistency", "creativity"])
        assert abs(sum(rn.values()) - 1.0) < 1e-6
        assert abs(rn["consistency"] - 0.5) < 1e-6
        assert abs(rn["creativity"] - 0.5) < 1e-6

    def test_zero_weights_equal_fallback(self, default_weights):
        rn = renormalize({**default_weights, "consistency": 0}, ["a", "b"])
        assert abs(rn["a"] - 0.5) < 1e-6
        assert abs(rn["b"] - 0.5) < 1e-6

    def test_empty_present(self, default_weights):
        rn = renormalize(default_weights, [])
        assert rn == {}


class TestAuditAggregator:
    @pytest.fixture
    def aggregator(self, default_weights):
        specialists = [
            FakeSpecialist("consistency", 80.0),
            FakeSpecialist("creativity", 60.0),
            FakeSpecialist("reader_hook", 70.0),
            FakeSpecialist("emotion_curve", 50.0),
            FakeSpecialist("style", 65.0),
            FakeSpecialist("factual", 90.0),
            FakeSpecialist("structure", 55.0),
            FakeSpecialist("multimodal", 40.0),
        ]
        return AuditAggregator(specialists=specialists, weights=default_weights)

    @pytest.mark.asyncio
    async def test_run_all_parallel(self, aggregator):
        ctx = {"book_id": 1, "chapter_number": 1}
        results = await aggregator.run_all(ctx)
        assert len(results) == 8
        assert all(isinstance(r, SpecialistAuditResult) for r in results.values())

    @pytest.mark.asyncio
    async def test_aggregate_all_present(self, aggregator):
        ctx = {"book_id": 1, "chapter_number": 1}
        await aggregator.run_all(ctx)
        result = aggregator.aggregate()

        assert isinstance(result, BookScoreResult)
        assert 0 <= result.overall <= 100
        assert len(result.by_specialist) == 8
        assert result.missing == []
        assert abs(sum(result.weights_used.values()) - 1.0) < 1e-6
        expected = (80 + 60 + 70 + 50 + 65 + 90 + 55 + 40) / 8
        assert abs(result.overall - expected) < 1e-6

    @pytest.mark.asyncio
    async def test_aggregate_with_missing(self, default_weights):
        specialists = [
            FakeSpecialist("consistency", 80.0),
            FakeSpecialist("creativity", 60.0),
        ]
        agg = AuditAggregator(specialists=specialists, weights=default_weights)
        ctx = {"book_id": 1, "chapter_number": 1}
        await agg.run_all(ctx)
        result = agg.aggregate()

        assert len(result.by_specialist) == 2
        assert len(result.missing) == 6
        assert abs(sum(result.weights_used.values()) - 1.0) < 1e-6
        assert all(abs(w - 0.5) < 1e-6 for w in result.weights_used.values())

    @pytest.mark.asyncio
    async def test_crashed_specialist_treated_as_missing(self, default_weights):
        specialists = [
            FakeSpecialist("consistency", 80.0),
            FakeSpecialist("creativity", 60.0),
            FakeSpecialist("factual", 0.0, should_fail=True),
        ]
        agg = AuditAggregator(specialists=specialists, weights=default_weights)
        ctx = {"book_id": 1, "chapter_number": 1}
        await agg.run_all(ctx)
        result = agg.aggregate()

        assert "factual" in result.missing
        assert "consistency" in result.by_specialist
        assert "creativity" in result.by_specialist

    @pytest.mark.asyncio
    async def test_degraded_with_score_counted(self, default_weights):
        specialists = [
            FakeSpecialist("consistency", 80.0),
            FakeSpecialist("creativity", 60.0, degraded=True),
            FakeSpecialist("reader_hook", 70.0),
        ]
        agg = AuditAggregator(specialists=specialists, weights=default_weights)
        ctx = {"book_id": 1, "chapter_number": 1}
        await agg.run_all(ctx)
        result = agg.aggregate()

        assert "creativity" in result.by_specialist
        assert len(result.by_specialist) == 3

    @pytest.mark.asyncio
    async def test_lowest_dimension(self, aggregator):
        ctx = {"book_id": 1, "chapter_number": 1}
        await aggregator.run_all(ctx)
        result = aggregator.aggregate()
        assert result.lowest_dimension() == "multimodal"

    @pytest.mark.asyncio
    async def test_events_published(self, default_weights):
        mock_bus = MagicMock()
        mock_bus.publish_async = AsyncMock()

        specialists = [FakeSpecialist("consistency", 80.0)]
        agg = AuditAggregator(specialists=specialists, weights=default_weights, event_bus=mock_bus)
        ctx = {"book_id": 1, "chapter_number": 1, "correlation_id": "test-1"}
        await agg.run_all(ctx)

        assert mock_bus.publish_async.call_count == 2


class TestBookScoreResult:
    def test_to_dict(self):
        result = BookScoreResult(
            overall=75.5,
            by_specialist={"consistency": 80.0, "creativity": 60.0},
            missing=["factual"],
            weights_used={"consistency": 0.5, "creativity": 0.5},
            raw={},
        )
        d = result.to_dict()
        assert d["overall"] == 75.5
        assert d["by_specialist"]["consistency"] == 80.0
        assert d["missing"] == ["factual"]
        assert d["lowest_dimension"] == "creativity"