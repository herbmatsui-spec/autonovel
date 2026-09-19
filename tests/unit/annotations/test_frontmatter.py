"""Tests for frontmatter parser."""
from __future__ import annotations

import pytest

from src.annotations.frontmatter import parse_frontmatter, serialize_frontmatter
from src.annotations.beat import EmotionalBeat
from src.pipeline.emotional_residue import EmotionType


class TestFrontmatterParser:
    """フロントマターパーサーテスト"""

    def test_parse_basic_frontmatter(self):
        """基本的なフロントマターパース"""
        text = """---
beats:
  - source: "A"
    target: "B"
    emotion: "fear"
    delta: 0.6
    cause: "ep14 betrayal"
    confidence: 0.9
    hidden: true
---
A「行くぞ」
B「待ちなさい」"""
        
        clean, beats = parse_frontmatter(text)
        
        assert len(beats) == 1
        beat = beats[0]
        assert beat.source == "A"
        assert beat.target == "B"
        assert beat.emotion == EmotionType.FEAR
        assert beat.delta == 0.6
        assert beat.cause == "ep14 betrayal"
        assert beat.confidence == 0.9
        assert beat.hidden is True
        assert "A「行くぞ」" in clean
        assert "---" not in clean

    def test_parse_multiple_beats(self):
        """複数ビートのパース"""
        text = """---
beats:
  - source: "A"
    target: "B"
    emotion: "affection"
    delta: 0.3
  - source: "B"
    target: "A"
    emotion: "tension"
    delta: -0.2
---
本文"""
        
        clean, beats = parse_frontmatter(text)
        
        assert len(beats) == 2
        assert beats[0].emotion == EmotionType.AFFECTION
        assert beats[0].delta == 0.3
        assert beats[1].emotion == EmotionType.TENSION
        assert beats[1].delta == -0.2

    def test_parse_no_frontmatter(self):
        """フロントマターなし"""
        text = "普通の本文です。"
        clean, beats = parse_frontmatter(text)
        
        assert beats == []
        assert clean == text

    def test_parse_invalid_yaml(self):
        """不正なYAML"""
        text = """---
beats:
  - source: "A"
    invalid: yaml: here
---
本文"""
        
        clean, beats = parse_frontmatter(text)
        
        assert beats == []
        assert clean == text

    def test_parse_missing_beats_key(self):
        """beatsキーなし"""
        text = """---
other_key: value
---
本文"""
        
        clean, beats = parse_frontmatter(text)
        
        assert beats == []
        assert "本文" in clean

    def test_parse_missing_closing_delimiter(self):
        """閉じデリミタなし"""
        text = """---
beats:
  - source: "A"
    target: "B"
    emotion: "fear"
    delta: 0.6
    cause: "test"
本文"""
        
        clean, beats = parse_frontmatter(text)
        
        assert beats == []
        assert clean == text

    def test_serialize_frontmatter(self):
        """フロントマターシリアライズ"""
        beats = [
            EmotionalBeat(
                episode=1, scene=1, source="A", target="B",
                emotion=EmotionType.FEAR, delta=0.6,
                cause="test", confidence=0.9, hidden=True,
            )
        ]
        
        fm_text = serialize_frontmatter(beats)
        
        assert fm_text.startswith("---\n")
        assert fm_text.endswith("---\n")
        assert "beats:" in fm_text
        assert "source: A" in fm_text  # YAML doesn't quote simple strings
        assert "emotion: fear" in fm_text
        assert "hidden: true" in fm_text

    def test_roundtrip(self):
        """パース→シリアライズのラウンドトリップ"""
        original = """---
beats:
  - source: "A"
    target: "B"
    emotion: "fear"
    delta: 0.6
    cause: "test"
    confidence: 0.9
    hidden: true
---
本文"""
        
        clean, beats = parse_frontmatter(original)
        serialized = serialize_frontmatter(beats)
        
        # 再パースして同じビートが得られるか
        clean2, beats2 = parse_frontmatter(serialized + "本文")
        
        assert len(beats2) == len(beats)
        assert beats2[0].source == beats[0].source
        assert beats2[0].target == beats[0].target
        assert beats2[0].emotion == beats[0].emotion
        assert beats2[0].delta == beats[0].delta


class TestFrontmatterIntegration:
    """インテグレーションテスト（インライン併用想定）"""

    def test_frontmatter_only(self):
        """フロントマターのみの場合"""
        text = """---
beats:
  - source: "A"
    target: "B"
    emotion: "fear"
    delta: 0.8
    cause: "ep14 event"
---
シーン本文"""
        
        clean, beats = parse_frontmatter(text)
        assert len(beats) == 1
        assert beats[0].delta == 0.8