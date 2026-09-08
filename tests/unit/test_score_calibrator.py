"""Unit tests for ScoreCalibrator (Part 2 / Step 18 / Checkpoint 3)."""

import pytest
from src.services.score_calibrator import (
    ScoreCalibrator,
    CalibrationConfig,
    DEFAULT_SPECIALIST_PRIORS,
    GENRE_PRIOR_OFFSETS,
    sigmoid_scale,
)


def test_calibration_config_defaults():
    """Verify default parameters of CalibrationConfig."""
    cfg = CalibrationConfig()
    assert cfg.target_mean == 65.0
    assert cfg.target_std == 12.0
    assert cfg.confidence_weight == 0.30
    assert cfg.outlier_threshold_z == 2.5
    assert cfg.clamp_min == 10.0
    assert cfg.clamp_max == 98.0


def test_genre_prior_stats():
    """Verify genre-specific mean score offsets."""
    calibrator = ScoreCalibrator()
    # Fantasy: creativity base 58.0 + 3.0 = 61.0
    mean_fantasy, std = calibrator.get_prior_stats("creativity", genre="fantasy")
    assert mean_fantasy == 61.0
    assert std == DEFAULT_SPECIALIST_PRIORS["creativity"][1]

    # General: base mean 58.0
    mean_general, _ = calibrator.get_prior_stats("creativity", genre="general")
    assert mean_general == 58.0


def test_calibrate_single_mean_identity():
    """When raw score equals prior mean, standardized score should be exactly target mean."""
    calibrator = ScoreCalibrator()
    prior_mean, _ = calibrator.get_prior_stats("structure", genre="general")
    score, meta = calibrator.calibrate_single("structure", raw_score=prior_mean, confidence=1.0)
    assert score == 65.0
    assert meta["z_score"] == 0.0
    assert meta["is_outlier"] is False


def test_bayesian_shrinkage_on_low_confidence():
    """Low confidence should shrink the score towards the target mean (65.0)."""
    calibrator = ScoreCalibrator()
    # High raw score
    score_high_conf, _ = calibrator.calibrate_single("reader_hook", raw_score=95.0, confidence=1.0)
    score_low_conf, meta = calibrator.calibrate_single("reader_hook", raw_score=95.0, confidence=0.2)

    # Low confidence score should be pulled closer to 65.0 than high confidence score
    assert score_high_conf > score_low_conf
    assert abs(score_low_conf - 65.0) < abs(score_high_conf - 65.0)
    assert meta["confidence"] == 0.2


def test_outlier_detection():
    """Extremely high or low scores exceeding threshold_z should be flagged as outliers."""
    calibrator = ScoreCalibrator()
    # consistency prior: mean 70.0, std 10.0
    # raw_score 20.0 -> z = (20 - 70) / 10 = -5.0 (outlier)
    score, meta = calibrator.calibrate_single("consistency", raw_score=20.0, confidence=1.0)
    assert meta["is_outlier"] is True
    assert meta["z_score"] <= -2.5


def test_sigmoid_scale_bounds():
    """Verify smooth sigmoid bounds clamp extreme values gracefully."""
    v_extreme_low = sigmoid_scale(-100.0)
    v_extreme_high = sigmoid_scale(200.0)
    assert 10.0 <= v_extreme_low <= 15.0
    assert 90.0 <= v_extreme_high <= 98.0


def test_calibrate_all_batch():
    """Test batch calibration of 8 specialists with dictionary output."""
    calibrator = ScoreCalibrator()
    raw_dict = {
        "reader_hook": 85.0,
        "consistency": {"score": 70.0, "confidence": 0.9},
        "structure": 65.0,
        "emotion_curve": 50.0,
        "style": 80.0,
        "factual": 95.0,
        "creativity": 30.0,
        "multimodal": 60.0,
    }
    result = calibrator.calibrate_all(raw_dict, genre="fantasy")
    assert "calibrated_scores" in result
    assert "metadata" in result
    assert len(result["calibrated_scores"]) == 8
    for name, s in result["calibrated_scores"].items():
        assert 10.0 <= s <= 98.0
