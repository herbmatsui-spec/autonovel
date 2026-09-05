"""Unit tests for the anti-AI data models."""

from __future__ import annotations

import pytest

from src.services.anti_ai.models import (
    AICategory,
    AntiAIDetectionResult,
    CorrectionHistory,
    DEFAULT_CATEGORY_WEIGHTS,
    DEFAULT_SEVERITY,
    Severity,
    ViolationSpan,
    compute_total_score,
    normalise_score,
)


class TestViolationSpan:
    def test_length_is_end_minus_start(self):
        v = ViolationSpan(
            category=AICategory.SAME_STRUCTURE, start=5, end=15, matched_text="0123456789"
        )
        assert v.length == 10

    def test_length_zero_when_collapsed(self):
        v = ViolationSpan(
            category=AICategory.SAME_STRUCTURE, start=5, end=5, matched_text=""
        )
        assert v.length == 0

    def test_length_never_negative(self):
        v = ViolationSpan(
            category=AICategory.SAME_STRUCTURE, start=10, end=5, matched_text=""
        )
        assert v.length == 0

    def test_to_dict_uses_string_values(self):
        v = ViolationSpan(
            category=AICategory.HEDGING_PATTERNS,
            start=0,
            end=4,
            matched_text="test",
            severity=Severity.LOW,
            suggestion="alt",
        )
        d = v.to_dict()
        assert d["category"] == "HEDGING_PATTERNS"
        assert d["severity"] == "low"
        assert d["start"] == 0
        assert d["end"] == 4
        assert d["matched_text"] == "test"
        assert d["suggestion"] == "alt"


class TestNormaliseScore:
    def test_clamps_low(self):
        assert normalise_score(-5) == 0.0

    def test_clamps_high(self):
        assert normalise_score(150) == 100.0

    def test_passes_through_in_range(self):
        assert normalise_score(42) == 42.0
        assert normalise_score(0) == 0.0
        assert normalise_score(100) == 100.0

    def test_custom_floor_and_ceiling(self):
        assert normalise_score(150, floor=0, ceiling=200) == 150
        assert normalise_score(-50, floor=-100, ceiling=100) == -50


class TestComputeTotalScore:
    def test_all_clean_returns_100(self):
        scores = {c: 100.0 for c in AICategory}
        assert compute_total_score(scores) == 100.0

    def test_all_zero_returns_0(self):
        scores = {c: 0.0 for c in AICategory}
        assert compute_total_score(scores) == 0.0

    def test_missing_keys_treated_as_clean(self):
        # Only SAME_STRUCTURE is dirty; everything else is 100 (clean).
        scores = {AICategory.SAME_STRUCTURE: 0.0}
        result = compute_total_score(scores)
        assert 0 < result < 100  # NOT zero because other categories are clean

    def test_empty_scores_returns_100(self):
        # No data means "no violation detected" — defensive default.
        assert compute_total_score({}) == 100.0

    def test_custom_weights(self):
        scores = {AICategory.SAME_STRUCTURE: 50.0}
        # Give SAME_STRUCTURE a huge weight so the partial score matters.
        weights = {c: (10.0 if c == AICategory.SAME_STRUCTURE else 0.1) for c in AICategory}
        result = compute_total_score(scores, weights)
        # Roughly: (50*10 + 100*6*0.1) / (10 + 6*0.1) = 560 / 10.6 ≈ 52.8
        assert 50 < result < 60

    def test_total_in_valid_range_for_random_inputs(self):
        # Run 50 random-ish scenarios and make sure we never escape [0, 100].
        for i in range(50):
            scores = {c: float(i * 7 % 101) for c in AICategory}
            total = compute_total_score(scores)
            assert 0 <= total <= 100


class TestAntiAIDetectionResult:
    def test_default_is_clean(self):
        r = AntiAIDetectionResult()
        assert r.total_score == 100.0
        assert r.violations == []
        assert r.method == "rule_based"
        assert r.category_scores == {}

    def test_to_dict_is_json_safe(self):
        r = AntiAIDetectionResult(
            category_scores={AICategory.SAME_STRUCTURE: 80.0},
            total_score=85.0,
            violations=[
                ViolationSpan(
                    category=AICategory.SAME_STRUCTURE,
                    start=0,
                    end=4,
                    matched_text="test",
                )
            ],
        )
        d = r.to_dict()
        assert d["total_score"] == 85.0
        assert d["method"] == "rule_based"
        assert d["category_scores"]["SAME_STRUCTURE"] == 80.0
        assert len(d["violations"]) == 1
        assert d["violations"][0]["category"] == "SAME_STRUCTURE"


class TestCorrectionHistory:
    def test_round_trip(self):
        h = CorrectionHistory(
            iteration=1,
            input_score=50.0,
            output_score=80.0,
            violations_found=10,
            violations_corrected=8,
            corrected_text="rewritten",
        )
        d = h.to_dict()
        assert d["iteration"] == 1
        assert d["input_score"] == 50.0
        assert d["output_score"] == 80.0
        assert d["violations_found"] == 10
        assert d["violations_corrected"] == 8


class TestDefaults:
    def test_severity_for_every_category(self):
        for c in AICategory:
            assert c in DEFAULT_SEVERITY

    def test_weights_for_every_category(self):
        for c in AICategory:
            assert c in DEFAULT_CATEGORY_WEIGHTS
            assert DEFAULT_CATEGORY_WEIGHTS[c] >= 0
