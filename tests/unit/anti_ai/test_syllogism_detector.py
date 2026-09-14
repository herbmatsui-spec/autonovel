"""
Unit tests for EmotionSyllogismDetector.
PLAN 03 - Step 2: 感情の三段論法検知器の単体テスト作成（TDD先行）
"""
from __future__ import annotations

import pytest
from src.services.anti_ai.detectors import EmotionSyllogismDetector
from src.services.anti_ai.models import AICategory


def test_detect_syllogism_pattern():
    """感情の説明・自己説得・三段論法構文が検出されること"""
    detector = EmotionSyllogismDetector()
    text = "彼は怒りを感じた。なぜなら大切な仲間を侮辱されたからだ。しかし、今は耐えるべきだと自分に言い聞かせた。"
    violations = detector.detect(text)
    assert len(violations) >= 1
    assert any("なぜなら" in v.matched_text or "言い聞かせた" in v.matched_text for v in violations)
    assert violations[0].category == AICategory.EMOTION_SYLLOGISM


def test_detect_syllogism_clean_prose():
    """生理的反応や生々しい呟き（クリーンな人間的描写）では違反が検出されないこと"""
    detector = EmotionSyllogismDetector()
    text = "男の罵倒に、奥歯が軋むほど噛み締められた。喉の奥に苦い胃液が競り上がる。『絶対に殺す』――ただそれだけを頭の中で反芻していた。"
    violations = detector.detect(text)
    assert len(violations) == 0
