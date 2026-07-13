"""
tests/test_erotic_thresholds.py
官能閾値のユニットテスト。
"""
from config.erotic_thresholds import (
    AFTERGLOW_MIN_CHARS,
    AFTERGLOW_MIN_PARAGRAPHS,
    DIVERSITY_SCORE_FAIL,
    DIVERSITY_SCORE_PASS,
    DIVERSITY_SCORE_WARN,
    INTENSITY_EXTREME,
    INTENSITY_R15,
    INTENSITY_SAFE_MAX,
)


def test_diversity_thresholds_order():
    assert DIVERSITY_SCORE_PASS > DIVERSITY_SCORE_WARN >= DIVERSITY_SCORE_FAIL


def test_intensity_order():
    assert INTENSITY_SAFE_MAX < INTENSITY_R15 < INTENSITY_EXTREME


def test_afterglow_thresholds():
    assert AFTERGLOW_MIN_PARAGRAPHS >= 2
    assert AFTERGLOW_MIN_CHARS >= 400
