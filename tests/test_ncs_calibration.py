"""
tests/test_ncs_calibration.py
NCS キャリブレーションのユニットテスト。
"""
from src.services.ncs_calibration import NarrativeCoherenceScorer


def test_calibrate_diversity_threshold_with_data():
    scorer = NarrativeCoherenceScorer()
    training_data = [
        {"score": 0.8, "rating": 5},
        {"score": 0.7, "rating": 4},
        {"score": 0.4, "rating": 3},
        {"score": 0.2, "rating": 1},
    ]
    result = scorer.calibrate_diversity_threshold(training_data)
    assert "threshold_pass" in result
    assert "threshold_warn" in result
    assert result["threshold_pass"] > result["threshold_warn"]


def test_calibrate_diversity_threshold_empty():
    scorer = NarrativeCoherenceScorer()
    result = scorer.calibrate_diversity_threshold([])
    assert result["threshold_pass"] == 0.5
    assert result["threshold_warn"] == 0.3


def test_calibrate_diversity_threshold_all_good():
    scorer = NarrativeCoherenceScorer()
    training_data = [
        {"score": 0.8, "rating": 5},
        {"score": 0.9, "rating": 5},
    ]
    result = scorer.calibrate_diversity_threshold(training_data)
    assert result["threshold_pass"] == 0.8


def test_calculate_ncs_empty():
    scorer = NarrativeCoherenceScorer()
    assert scorer.calculate_ncs(0.0, 0.0, 0.0) == 0.0


def test_ncs_weights():
    scorer = NarrativeCoherenceScorer()
    assert abs(scorer.weights["plot_continuity"] +
               scorer.weights["character_consistency"] +
               scorer.weights["theme_unity"] - 1.0) < 0.001
