"""Unit tests for UnifiedBookScoreBridge (Part 3 / Step 30 / Checkpoint 5)."""

import pytest
from src.services.book_score_mapping import (
    UnifiedBookScoreBridge,
    Unified5DScore,
    BASE_TRANSFORMATION_MATRIX,
    DEFAULT_DIMENSION_WEIGHTS,
    PHASE_DIMENSION_SHIFTS,
    BOOK_SCORE_DIMENSIONS,
)


def test_transformation_matrix_validity():
    """Each dimension in BASE_TRANSFORMATION_MATRIX must sum to 1.0."""
    for dim, weights in BASE_TRANSFORMATION_MATRIX.items():
        total = sum(weights.values())
        assert abs(total - 1.0) < 1e-6, f"{dim} weights sum to {total}, expected 1.0"


def test_dimension_weights_sum_to_one():
    """Dimension weights across 5D must sum to 1.0."""
    total_default = sum(DEFAULT_DIMENSION_WEIGHTS.values())
    assert abs(total_default - 1.0) < 1e-6

    for phase, shifts in PHASE_DIMENSION_SHIFTS.items():
        total_phase = sum(shifts.values())
        assert abs(total_phase - 1.0) < 1e-6, f"{phase} shifts sum to {total_phase}, expected 1.0"


def test_identity_mapping():
    """If all specialists have identical score X, all 5 dimensions and overall should be X."""
    bridge = UnifiedBookScoreBridge()
    scores = {
        "consistency": 80.0,
        "creativity": 80.0,
        "reader_hook": 80.0,
        "emotion_curve": 80.0,
        "style": 80.0,
        "factual": 80.0,
        "structure": 80.0,
        "multimodal": 80.0,
    }
    res = bridge.map_to_5d(scores, genre="general", phase="draft")
    assert res.overall_score == 80.0
    assert res.structure_score == 80.0
    assert res.coherency_score == 80.0
    assert res.factual_grounding_score == 80.0
    assert res.visual_textual_synergy_score == 80.0
    assert res.reader_experience_score == 80.0


def test_genre_override_mapping():
    """Mystery genre should emphasize consistency in coherency_score."""
    bridge = UnifiedBookScoreBridge()
    # High consistency (90), lower style (50) and structure (50)
    scores = {
        "consistency": 90.0,
        "style": 50.0,
        "structure": 50.0,
        "factual": 50.0,
        "multimodal": 50.0,
        "creativity": 50.0,
        "reader_hook": 50.0,
        "emotion_curve": 50.0,
    }
    res_general = bridge.map_to_5d(scores, genre="general")
    res_mystery = bridge.map_to_5d(scores, genre="mystery")

    # In mystery, consistency weight is 0.75 vs 0.65 in general, so coherency_score should be higher
    assert res_mystery.coherency_score > res_general.coherency_score


def test_phase_dynamic_shifts():
    """Plot phase should weigh structure and coherency higher."""
    bridge = UnifiedBookScoreBridge()
    weights_plot = bridge.get_dimension_weights_for_phase("plot")
    weights_draft = bridge.get_dimension_weights_for_phase("draft")

    assert weights_plot["structure_score"] == 0.35
    assert weights_draft["structure_score"] == 0.15
    assert weights_draft["reader_experience_score"] == 0.30


def test_proportional_renormalization_missing_specialists():
    """Missing specialists should proportionally re-normalize remaining weights."""
    bridge = UnifiedBookScoreBridge()
    # Only factual available for factual_grounding_score (normally factual 0.75 + consistency 0.25)
    # If factual has 88.0 and consistency is missing, factual_grounding_score should be exactly 88.0
    scores = {
        "factual": 88.0,
        "structure": 75.0,
        "reader_hook": 80.0,
        "emotion_curve": 70.0,
    }
    res = bridge.map_to_5d(scores, genre="general")
    assert res.factual_grounding_score == 88.0
    assert "consistency" in res.missing_specialists


def test_lowest_dimension_identification():
    """Lowest dimension method should correctly pick the 5D minimum."""
    bridge = UnifiedBookScoreBridge()
    scores = {
        "consistency": 85.0,
        "creativity": 85.0,
        "reader_hook": 85.0,
        "emotion_curve": 40.0,  # low
        "style": 85.0,
        "factual": 85.0,
        "structure": 85.0,
        "multimodal": 85.0,
    }
    res = bridge.map_to_5d(scores, genre="general")
    assert res.lowest_dimension() == "reader_experience_score"
