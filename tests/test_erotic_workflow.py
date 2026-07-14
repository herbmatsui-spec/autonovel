"""
tests/test_erotic_workflow.py
官能ワークフローのユニットテスト。
"""

from config.erotic_pacing import EroticCurve
from config.erotic_platform_presets import get_preset, get_preset_names
from config.erotic_vocabulary import get_vocabulary_for_tier
from formatters.erotic_censor import apply_censorship
from src.agents.erotic_integrity import EroticIntegrityChecker
from src.engine.prompts.erotic_specialist import EroticSpecialist
from src.services.erotic_density_controller import EroticDensityController
from src.services.erotic_diversity_score import check_diversity, classify_diversity


def test_erotic_curve_creation():
    curve = EroticCurve.create_default(3)
    assert len(curve.beats) == 3
    assert curve.get_peak_beat().phase == "peak"


def test_safety_manifest_included_in_prompt():
    specialist = EroticSpecialist()
    curve = EroticCurve.create_default(2)
    prompt = specialist.build_scene_prompt(curve, {})
    assert "官能描写セーフティ・マニフェスト" in prompt


def test_metaphor_filter():
    specialist = EroticSpecialist()
    result = specialist.metaphor_filter("セックスをした", 1)
    assert "セックス" not in result


def test_censorship_kakuyomu():
    result = apply_censorship("二人の夜は続いた。", "kakuyomu_romance")
    assert "◆" in result


def test_censorship_selfhost():
    result = apply_censorship("二人の夜は続いた", "adult_selfhost")
    assert "◆" not in result


def test_density_controller():
    controller = EroticDensityController()
    assert controller.should_allow_peak([1, 2, 3]) is True
    assert controller.should_allow_peak([4, 5]) is False


def test_integrity_checker():
    checker = EroticIntegrityChecker()
    ok, issues, quality_report, continuity_report = checker.check_all(
        "二人は唇が触れる距離で、彼が求めて彼女が応じる"
    )
    assert ok is True


def test_vocabulary_tiers():
    mild = get_vocabulary_for_tier("mild")
    full = get_vocabulary_for_tier("full")
    assert len(full["metaphors"]) > len(mild["metaphors"])


def test_nsfw_disabled_no_erotic():
    """NSFW無効時に erotic_intensity=0 であることを確認"""
    intensity = 0
    curve = EroticCurve.create_default(intensity)
    assert curve.target_intensity == 0


def test_platform_presets():
    names = get_preset_names()
    assert len(names) == 3
    kakuyomu = get_preset("kakuyomu_romance")
    assert kakuyomu["max_intensity"] == 2


# Step 12: 多様性スコア閾値テスト
def test_diversity_classify():
    assert classify_diversity(0.6) == "pass"
    assert classify_diversity(0.4) == "warn"
    assert classify_diversity(0.2) == "fail"
    assert classify_diversity(0.5) == "pass"


def test_diversity_check():
    from config.erotic_vocabulary import METAPHOR_BANK

    result = check_diversity("瞳を星の瞬きに例える 声が風鈴の音に例える", METAPHOR_BANK)
    assert "score" in result
    assert "classification" in result
    assert "warnings" in result


# Step 19: 同意検証テスト
def test_consent_explicit_detected():
    checker = EroticIntegrityChecker()
    ok, issues = checker.check_consent_state("彼が同意を求めて、彼女がOKと言った", "explicit")
    assert ok is True


def test_consent_explicit_missing():
    checker = EroticIntegrityChecker()
    ok, issues = checker.check_consent_state("二人は黙って近づいた", "explicit")
    assert ok is False
    assert any("明示的同意" in i for i in issues)


def test_consent_refusal_detected():
    checker = EroticIntegrityChecker()
    ok, issues = checker.check_consent_state("彼女は嫌だと言い、逃げた", "implicit")
    assert ok is False
    assert any("拒否表現" in i for i in issues)


def test_consent_implicit_ok():
    checker = EroticIntegrityChecker()
    ok, issues = checker.check_consent_state("二人は唇が触れる距離で", "implicit")
    assert ok is True


def test_check_all_with_consent():
    checker = EroticIntegrityChecker()
    text = "彼女は服を着ている"
    ok, issues, quality_report, continuity_report = checker.check_all(
        text, consent_state="explicit"
    )
    assert ok is False
    assert any("明示的同意" in issue for issue in issues)


# Step 30: 密度管理シナリオテスト
def test_density_controller_book_scenario():
    controller = EroticDensityController()
    assert controller.should_allow_peak([1, 2, 3, 4, 4, 4]) is False
    assert controller.should_allow_peak([1, 2, 3, 4, 4, 3]) is True
    assert controller.should_allow_peak([1, 2, 3, 4, 3, 4]) is True


def test_density_controller_recommend_intensity():
    controller = EroticDensityController()
    assert controller.recommend_intensity(1, 10, 4) <= 2
    assert controller.recommend_intensity(9, 10, 4) >= 4


def test_density_controller_suggest_next():
    controller = EroticDensityController()
    assert controller.suggest_next_intensity([1, 2, 3], 4) == 4
    assert controller.suggest_next_intensity([1, 2, 4, 4], 4) == 3
    assert controller.suggest_next_intensity([1, 2, 3, 5], 4) == 3
    assert controller.suggest_next_intensity([1, 2, 4, 4], 1) == 1


# Step 33: 語彙ティア最小数確認テスト
def test_full_tier_minimum_vocabulary():
    from config.erotic_vocabulary import get_vocabulary_for_tier

    full = get_vocabulary_for_tier("full")
    assert len(full["metaphors"]) >= 30, f"metaphors: {len(full['metaphors'])}"
    assert len(full["onomatopoeia"]) >= 25, f"onomatopoeia: {len(full['onomatopoeia'])}"
    assert len(full["psychology"]) >= 20, f"psychology: {len(full['psychology'])}"


def test_intense_tier_accessible():
    from config.erotic_vocabulary_ext import get_vocabulary_for_tier_ext

    intense = get_vocabulary_for_tier_ext("intense")
    assert len(intense["metaphors"]) >= len(get_vocabulary_for_tier("full")["metaphors"])
