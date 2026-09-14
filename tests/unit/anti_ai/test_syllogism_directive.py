"""
Unit tests for syllogism rewrite directive generator.
PLAN 03 - Step 11: リライト指示生成器の検証
"""
from __future__ import annotations

import pytest
from src.services.anti_ai.detectors import EmotionSyllogismDetector
from src.services.anti_ai.rewrite_directive_generator import generate_syllogism_rewrite_directive


def test_generate_syllogism_rewrite_directive():
    """三段論法違反から具体的な身体言語置換指示が生成されること"""
    text = "彼は怒りを感じた。なぜなら仲間を侮辱されたからだ。今は耐えるべきだと自分に言い聞かせた。"
    detector = EmotionSyllogismDetector()
    violations = detector.detect(text)
    assert len(violations) >= 1

    directive = generate_syllogism_rewrite_directive(violations)
    assert "感情説明の外科的切除ディレクティブ" in directive
    assert "身体的生理反応" in directive
    assert "該当箇所" in directive


def test_generate_syllogism_rewrite_directive_empty_when_no_violations():
    """違反がない場合は空文字列を返すこと"""
    directive = generate_syllogism_rewrite_directive([])
    assert directive == ""
