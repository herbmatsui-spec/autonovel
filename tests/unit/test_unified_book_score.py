"""Unit and integration tests for Unified BookScore & Maturity Reports (Part 3 / Step 36 / Checkpoint 6)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.book_score_service import BookScore, BookScoreCalculator


def test_calculate_from_specialists_delegation():
    """Verify BookScoreCalculator.calculate_from_specialists produces accurate 5D scores."""
    calc = BookScoreCalculator()
    specialist_scores = {
        "consistency": 85.0,
        "creativity": 80.0,
        "reader_hook": 90.0,
        "emotion_curve": 85.0,
        "style": 85.0,
        "factual": 90.0,
        "structure": 88.0,
        "multimodal": 82.0,
    }
    score = calc.calculate_from_specialists(specialist_scores, genre="fantasy", phase="draft")

    assert isinstance(score, BookScore)
    assert score.overall_score >= 80.0
    assert score.structure_score >= 80.0
    assert score.coherency_score >= 80.0
    assert score.factual_grounding_score >= 80.0
    assert score.visual_textual_synergy_score >= 80.0
    assert score.reader_experience_score >= 80.0
    assert score.specialist_breakdown is not None
    assert "contributions" in score.specialist_breakdown


def test_score_contributions_breakdown():
    """Verify get_score_contributions returns point breakdown for each dimension."""
    calc = BookScoreCalculator()
    specialist_scores = {
        "consistency": 90.0,
        "creativity": 70.0,
        "reader_hook": 80.0,
        "emotion_curve": 75.0,
        "style": 85.0,
        "factual": 95.0,
        "structure": 85.0,
        "multimodal": 80.0,
    }
    contributions = calc.get_score_contributions(specialist_scores, genre="general")
    assert "structure_score" in contributions
    assert "factual_grounding_score" in contributions
    # Factual grounding: factual (95 * 0.75 = 71.25) + consistency (90 * 0.25 = 22.5) = 93.75
    fg = contributions["factual_grounding_score"]
    assert "factual" in fg
    assert "consistency" in fg
    assert abs((fg["factual"] + fg["consistency"]) - 93.75) < 0.1


def test_bidirectional_mappings():
    """Verify forward and reverse specialist mappings align correctly."""
    calc = BookScoreCalculator()
    fwd = calc.get_dimension_to_specialists_mapping(genre="general")
    rev = calc.get_specialist_to_dimensions_mapping(genre="general")

    assert "structure_score" in fwd
    assert "structure" in rev
    # structure specialist is in structure_score and coherency_score
    assert "structure_score" in rev["structure"]
    assert "coherency_score" in rev["structure"]
    assert rev["structure"]["structure_score"] == fwd["structure_score"]["structure"]


def test_maturity_report_grades_and_targets():
    """Verify generate_maturity_report categorizes S (commercial 85+) and A (web hit 75+) accurately."""
    calc = BookScoreCalculator()

    # Commercial-ready score (>= 85.0)
    score_s = BookScore(
        overall_score=87.5,
        structure_score=88.0,
        coherency_score=89.0,
        factual_grounding_score=86.0,
        visual_textual_synergy_score=85.0,
        reader_experience_score=88.0,
    )
    rep_s = calc.generate_maturity_report(score_s)
    assert rep_s["rank"] == "S"
    assert rep_s["is_commercial_ready"] is True
    assert rep_s["is_web_hit_ready"] is True

    # Web-hit ready score (75.0 - 84.9)
    score_a = BookScore(
        overall_score=78.0,
        structure_score=76.0,
        coherency_score=80.0,
        factual_grounding_score=75.0,
        visual_textual_synergy_score=72.0,  # lowest
        reader_experience_score=82.0,
    )
    rep_a = calc.generate_maturity_report(score_a)
    assert rep_a["rank"] == "A"
    assert rep_a["is_commercial_ready"] is False
    assert rep_a["is_web_hit_ready"] is True
    assert rep_a["lowest_dimension"] == "visual_textual_synergy_score"


@pytest.mark.asyncio
async def test_save_score_includes_specialist_breakdown():
    """Verify save_score passes specialist_breakdown to BookScoreModel in repository."""
    mock_repo = MagicMock()
    mock_repo.save = AsyncMock()

    calc = BookScoreCalculator(repository=mock_repo)
    score = BookScore(
        overall_score=82.0,
        structure_score=80.0,
        coherency_score=85.0,
        factual_grounding_score=80.0,
        visual_textual_synergy_score=80.0,
        reader_experience_score=85.0,
        specialist_breakdown={"test": "data"},
    )
    await calc.save_score(book_id=10, chapter_number=1, score=score)

    assert mock_repo.save.called
    saved_model = mock_repo.save.call_args[0][0]
    assert saved_model.specialist_breakdown == {"test": "data"}
    assert saved_model.overall_score == 82.0
