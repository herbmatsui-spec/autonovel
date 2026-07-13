"""
tests/integration/test_erotic_full_pipeline.py
エンドツーエンドのスモークテスト。
"""
from unittest.mock import AsyncMock, MagicMock

import pytest

from config.erotic_pacing import EroticCurve
from config.erotic_platform_presets import get_preset, get_preset_names
from config.erotic_vocabulary import get_vocabulary_for_tier
from formatters.erotic_censor import apply_censorship
from src.agents.erotic_integrity import EroticIntegrityChecker
from src.backend.workflows.refine_erotic_workflow import RefineEroticWorkflow
from src.services.erotic_density_controller import EroticDensityController
from src.services.erotic_diversity_score import classify_diversity, compute_diversity_score


def test_erotic_curve_default_r15():
    curve = EroticCurve.create_default(3)
    assert curve.target_intensity == 3
    assert len(curve.beats) == 3
    peak = curve.get_peak_beat()
    assert peak.phase == "peak"
    assert peak.consent_state == "explicit"


def test_vocabulary_tier_intensity_mapping():
    mild = get_vocabulary_for_tier("mild")
    moderate = get_vocabulary_for_tier("moderate")
    full = get_vocabulary_for_tier("full")
    assert len(full["metaphors"]) > len(mild["metaphors"])
    assert len(moderate["metaphors"]) >= len(mild["metaphors"])


def test_nocturn_preset_censorship():
    preset = get_preset("nocturn_novel")
    assert preset["max_intensity"] == 3
    text = "二人の夜は続いた。セックスは不快。"
    censored = apply_censorship(text, "nocturn_novel")
    assert "◆" in censored


def test_adult_preset_no_censorship():
    preset = get_preset("adult_selfhost")
    text = "二人の夜は続いた"
    censored = apply_censorship(text, "adult_selfhost")
    assert "◆" not in censored


def test_density_controller_allow_peak():
    controller = EroticDensityController()
    assert controller.should_allow_peak([1, 2, 3]) is True
    assert controller.should_allow_peak([4, 5]) is False
    assert controller.should_allow_peak([4, 3, 4]) is True


def test_integrity_checker_clothing():
    checker = EroticIntegrityChecker()
    ok, issues = checker.check_all("彼女は衣を解いた。静かに横たわる。")
    assert ok is True


def test_integrity_checker_consent_implicit_ok():
    checker = EroticIntegrityChecker()
    ok, issues = checker.check_consent_state("二人は唇が触れる距離まで近づいた", "implicit")
    assert ok is True


def test_diversity_score_compute():
    from config.erotic_vocabulary import METAPHOR_BANK
    text = "瞳を星の瞬きに例える 声が風鈴の音に例える 体温を夕暮れの大地に例える"
    score = compute_diversity_score(text, METAPHOR_BANK)
    assert 0.0 <= score <= 1.0


def test_platform_preset_count():
    names = get_preset_names()
    assert len(names) == 3
    assert "nocturn_novel" in names
    assert "kakuyomu_romance" in names
    assert "adult_selfhost" in names


def test_intensity_scale_r15():
    from config.erotic_thresholds import INTENSITY_EXTREME, INTENSITY_R15, INTENSITY_SAFE_MAX
    assert INTENSITY_SAFE_MAX < INTENSITY_R15 < INTENSITY_EXTREME


def test_diversity_threshold_pass():
    assert classify_diversity(0.6) == "pass"


def test_diversity_threshold_warn():
    assert classify_diversity(0.4) == "warn"


def test_diversity_threshold_fail():
    assert classify_diversity(0.2) == "fail"


def test_avg_intensity():
    controller = EroticDensityController()
    avg = controller.compute_avg_intensity([1, 2, 3, 4, 5])
    assert avg == 3.0
    assert controller.compute_avg_intensity([]) == 0.0


@pytest.mark.asyncio
async def test_refine_erotic_workflow_mock():
    mock_engine = MagicMock()
    mock_uow = MagicMock()
    mock_engine.repo.return_value.__aenter__.return_value = mock_uow

    mock_chapter = MagicMock()
    mock_chapter.content = "テストコンテンツ"
    mock_plot = MagicMock()

    mock_uow.chapters.get_chapter.return_value = mock_chapter
    mock_uow.plots.get_plot.return_value = mock_plot
    mock_uow.session.commit = AsyncMock()

    workflow = RefineEroticWorkflow()
    workflow.engine = mock_engine

    result = await workflow.execute(
        book_id=1,
        ep_num=1,
        intensity=2,
        platform_preset="kakuyomu_romance"
    )

    assert result["success"] is True
    assert result["is_ok"] is True
    assert result["intensity_applied"] == 2

    mock_uow.chapters.get_chapter.assert_called_once_with(1, 1)
    mock_uow.plots.get_plot.assert_called_once_with(1, 1)
    mock_uow.session.commit.assert_awaited_once()


def test_density_controller_average_intensity():
    controller = EroticDensityController()
    avg = controller.compute_avg_intensity([1, 2, 3, 4, 5])
    assert avg == 3.0
    assert controller.compute_avg_intensity([]) == 0.0
