"""Unit tests for Commercial Quality Benchmarks & Health Checks (Step 66 / Checkpoint 11)."""

import pytest
from src.services.commercial_benchmarks import CommercialBenchmarkJudge, CommercialQualityMetrics


def test_evaluate_quality_commercial_ready():
    """Test commercial publication readiness (85+ overall, no dimension < 70)."""
    dimensions = {
        "structure_score": 88.0,
        "character_score": 86.0,
        "coherency_score": 85.0,
        "worldview_score": 84.0,
        "theme_score": 87.0,
    }
    metrics = CommercialBenchmarkJudge.evaluate_quality(
        overall_score=86.0,
        dimension_scores=dimensions,
        specialist_scores={"reader_hook": 90.0, "style": 85.0},
    )
    assert metrics.is_commercial_ready is True
    assert metrics.is_web_hit_ready is True
    assert metrics.has_no_fatal_flaws is True
    assert metrics.rank == "S"
    assert "Sランク" in metrics.evaluation_summary

    data = metrics.to_dict()
    assert data["overall_score"] == 86.0
    assert data["rank"] == "S"
    assert data["is_commercial_ready"] is True


def test_evaluate_quality_web_hit_ready():
    """Test web hit readiness (75+ overall, no dimension < 65)."""
    dimensions = {
        "structure_score": 78.0,
        "character_score": 76.0,
        "coherency_score": 75.0,
        "worldview_score": 68.0,
        "theme_score": 77.0,
    }
    metrics = CommercialBenchmarkJudge.evaluate_quality(
        overall_score=76.5,
        dimension_scores=dimensions,
    )
    assert metrics.is_commercial_ready is False  # not >= 85
    assert metrics.is_web_hit_ready is True
    assert metrics.has_no_fatal_flaws is True
    assert metrics.rank == "A"
    assert "Aランク" in metrics.evaluation_summary


def test_evaluate_quality_fatal_flaws():
    """Test fatal flaw cutoff (any dimension < 60.0)."""
    dimensions = {
        "structure_score": 85.0,
        "character_score": 80.0,
        "coherency_score": 55.0,  # fatal flaw!
        "worldview_score": 80.0,
        "theme_score": 80.0,
    }
    metrics = CommercialBenchmarkJudge.evaluate_quality(
        overall_score=76.0,
        dimension_scores=dimensions,
    )
    assert metrics.has_no_fatal_flaws is False
    assert metrics.is_commercial_ready is False
    assert metrics.is_web_hit_ready is False  # dim min < 65


def test_validate_pdca_improvement():
    """Test PDCA score improvement percentage validation (>= 15%)."""
    # 70.0 -> 82.0 = (12 / 70) * 100 = 17.14% -> True
    passed, rate = CommercialBenchmarkJudge.validate_pdca_improvement(70.0, 82.0)
    assert passed is True
    assert rate >= 15.0

    # 70.0 -> 78.0 = (8 / 70) * 100 = 11.43% -> False
    passed_fail, rate_fail = CommercialBenchmarkJudge.validate_pdca_improvement(70.0, 78.0)
    assert passed_fail is False
    assert rate_fail < 15.0


def test_run_system_health_check_7_points():
    """Test 7-point health check verification across Pillar 4 PDCA components."""
    all_passed, checks = CommercialBenchmarkJudge.run_system_health_check()
    assert len(checks) == 7
    for check_name, status in checks.items():
        assert status is True, f"Health check failed for: {check_name}"
    assert all_passed is True
