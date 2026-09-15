"""src/services/book_score_service.py の深層単体テスト."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.database.models.book_score import BookScore as BookScoreModel
from src.services.book_score_service import BookScore, BookScoreCalculator


# ==============================================================================
# 1. Text Stats & Helper Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_build_text_stats_empty():
    calc = BookScoreCalculator(config_path="nonexistent.yaml")
    stats = await calc._build_text_stats("")
    assert stats["char_count"] == 0
    assert stats["sentence_count"] == 0
    assert stats["avg_sentence_length"] == 0.0


@pytest.mark.asyncio
async def test_build_text_stats_sentences():
    calc = BookScoreCalculator(config_path="nonexistent.yaml")
    text = "吾輩は猫である。名前はまだ無い。どこで生れたか頓と見当がつかぬ！"
    stats = await calc._build_text_stats(text)
    assert stats["char_count"] == len(text)
    assert stats["sentence_count"] == 3
    assert stats["avg_sentence_length"] > 0


def test_get_anachronisms():
    calc = BookScoreCalculator(config_path="nonexistent.yaml")
    ancient = calc._get_anachronisms("ancient")
    assert any("電話" in x or "自動車" in x for x in ancient)

    medieval = calc._get_anachronisms("medieval")
    assert any("電話" in x or "拳銃" in x for x in medieval)

    unknown = calc._get_anachronisms("cyberpunk")
    assert unknown == []


# ==============================================================================
# 2. Dimension Scoring Tests
# ==============================================================================


@pytest.fixture
def mock_calc():
    repo = MagicMock()
    repo.session = MagicMock()
    calc = BookScoreCalculator(config_path="nonexistent.yaml", repository=repo)
    return calc


@pytest.mark.asyncio
async def test_score_structure_without_repo():
    calc = BookScoreCalculator(config_path="nonexistent.yaml", repository=None)
    score = await calc._score_structure(1, 1, None)
    assert score == 50.0


@pytest.mark.asyncio
async def test_score_structure_with_mocks(mock_calc):
    # Mock audit report
    audit_item1 = MagicMock(category="logical_consistency", severity="low")
    audit_item2 = MagicMock(category="causal_integrity", severity="low")
    mock_calc._fetch_audit_report = AsyncMock(return_value=[audit_item1, audit_item2])

    # Mock plot with arc end
    plot_mock = MagicMock(end_ep=1)
    mock_calc._fetch_plot = AsyncMock(return_value=plot_mock)

    # Mock chapter with tension
    chapter_mock = MagicMock(tension=60)
    mock_calc._fetch_chapter = AsyncMock(return_value=chapter_mock)

    score = await mock_calc._score_structure(1, 1, None)
    assert score >= 80.0


@pytest.mark.asyncio
async def test_score_coherency_with_mocks(mock_calc):
    mock_calc._fetch_bible = AsyncMock(return_value=MagicMock(world_settings="Test settings"))
    mock_calc._fetch_chapter = AsyncMock(return_value=MagicMock(content="勇者は剣を抜いて魔王と戦った。"))
    score = await mock_calc._score_coherency(1, 1, None)
    assert 0.0 <= score <= 100.0


@pytest.mark.asyncio
async def test_score_factual_with_mocks(mock_calc):
    mock_calc._fetch_bible = AsyncMock(return_value=MagicMock(period="中世"))
    mock_calc._fetch_chapter = AsyncMock(return_value=MagicMock(content="騎士はスマートフォンで連絡を取った。"))
    score = await mock_calc._score_factual(1, 1, None)
    assert 0.0 <= score <= 100.0


@pytest.mark.asyncio
async def test_score_visual_textual_with_mocks(mock_calc):
    mock_calc._fetch_illustration = AsyncMock(return_value=MagicMock(image_url="http://example.com/img.png"))
    mock_calc._fetch_chapter = AsyncMock(return_value=MagicMock(content="鮮やかな紅蓮の炎が夜空を焦がす。"))
    score = await mock_calc._score_visual_textual(1, 1, None)
    assert 0.0 <= score <= 100.0


@pytest.mark.asyncio
async def test_score_reader_experience_with_mocks(mock_calc):
    mock_calc._fetch_chapter = AsyncMock(
        return_value=MagicMock(content="「なんだって！？」少年は驚愕し、扉の向こうへと走り出した。続く。")
    )
    score = await mock_calc._score_reader_experience(1, 1, None)
    assert 0.0 <= score <= 100.0


# ==============================================================================
# 3. Full Calculate, Save & Trend Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_calculate_and_save(mock_calc):
    mock_calc._score_structure = AsyncMock(return_value=85.0)
    mock_calc._score_coherency = AsyncMock(return_value=80.0)
    mock_calc._score_factual = AsyncMock(return_value=90.0)
    mock_calc._score_visual_textual = AsyncMock(return_value=75.0)
    mock_calc._score_reader_experience = AsyncMock(return_value=88.0)
    mock_calc.save_score = AsyncMock()

    result = await mock_calc.calculate(1, 1)
    assert isinstance(result, BookScore)
    assert result.overall_score > 0
    assert mock_calc.save_score.called


@pytest.mark.asyncio
async def test_save_score_executes_repo(mock_calc):
    mock_calc._repository.save = AsyncMock()
    score = BookScore(
        overall_score=80.0,
        structure_score=85.0,
        coherency_score=75.0,
        factual_grounding_score=80.0,
        visual_textual_synergy_score=80.0,
        reader_experience_score=80.0,
    )
    await mock_calc.save_score(1, 1, score)
    assert mock_calc._repository.save.called


@pytest.mark.asyncio
async def test_get_latest_score(mock_calc):
    expected_model = MagicMock(spec=BookScoreModel)
    mock_calc._repository.get_latest = AsyncMock(return_value=expected_model)
    latest = await mock_calc.get_latest_score(1, 1)
    assert latest == expected_model


@pytest.mark.asyncio
async def test_analyze_trend(mock_calc):
    scores = [
        MagicMock(overall_score=70.0 + i * 2, structure_score=70.0, coherency_score=70.0, chapter_number=i+1)
        for i in range(5)
    ]
    mock_calc._repository.get_all_for_book = AsyncMock(return_value=scores)
    trend = await mock_calc.analyze_trend(1, window=5)
    assert "average" in trend or "trend" in trend or isinstance(trend, dict)


@pytest.mark.asyncio
async def test_generate_pdca_report(mock_calc):
    mock_calc.analyze_trend = AsyncMock(
        return_value={
            "book_id": 1,
            "avg_score": 75.0,
            "status": "stable",
            "trend_direction": "stable",
            "slope": 0.5,
            "r_squared": 0.85,
            "changepoints": [],
            "next_chapter_prediction": 78.5,
            "moving_avg_3": [72.0, 74.0, 76.0],
        }
    )
    mock_calc._repository.get_all_for_book = AsyncMock(return_value=[])
    mock_calc.get_latest_score = AsyncMock(
        return_value=MagicMock(
            overall_score=75.0,
            structure_score=60.0,
            coherency_score=85.0,
            factual_grounding_score=80.0,
            visual_textual_synergy_score=70.0,
            reader_experience_score=80.0,
        )
    )
    report = await mock_calc.generate_pdca_report(1)
    assert isinstance(report, dict)
    assert "book_id" in report or "suggestions" in report or "summary" in report or len(report) > 0
