"""Tests for inline beat parser."""
from __future__ import annotations

import pytest

from src.annotations.parser import parse_beats, normalize_emotion
from src.pipeline.emotional_residue import EmotionType


class TestNormalizeEmotion:
    """感情タイプ正規化テスト"""

    def test_canonical_names(self):
        """正規名で正しく変換"""
        assert normalize_emotion("affection") == EmotionType.AFFECTION
        assert normalize_emotion("tension") == EmotionType.TENSION
        assert normalize_emotion("fear") == EmotionType.FEAR
        assert normalize_emotion("trust") == EmotionType.TRUST
        assert normalize_emotion("intimacy") == EmotionType.INTIMACY
        assert normalize_emotion("jealousy") == EmotionType.JEALOUSY
        assert normalize_emotion("anger") == EmotionType.ANGER
        assert normalize_emotion("sadness") == EmotionType.SADNESS
        assert normalize_emotion("surprise") == EmotionType.SURPRISE
        assert normalize_emotion("disgust") == EmotionType.DISGUST

    def test_aliases(self):
        """エイリアスで正しく変換"""
        assert normalize_emotion("aff") == EmotionType.AFFECTION
        assert normalize_emotion("ten") == EmotionType.TENSION
        assert normalize_emotion("fea") == EmotionType.FEAR
        assert normalize_emotion("tru") == EmotionType.TRUST
        assert normalize_emotion("int") == EmotionType.INTIMACY
        assert normalize_emotion("jel") == EmotionType.JEALOUSY
        assert normalize_emotion("ang") == EmotionType.ANGER
        assert normalize_emotion("sad") == EmotionType.SADNESS
        assert normalize_emotion("sur") == EmotionType.SURPRISE
        assert normalize_emotion("dis") == EmotionType.DISGUST

    def test_case_insensitive(self):
        """大文字小文字不問"""
        assert normalize_emotion("FEAR") == EmotionType.FEAR
        assert normalize_emotion("Fear") == EmotionType.FEAR
        assert normalize_emotion("AfF") == EmotionType.AFFECTION

    def test_unknown_defaults_to_affection(self):
        """未知はaffectionにフォールバック"""
        assert normalize_emotion("unknown") == EmotionType.AFFECTION
        assert normalize_emotion("gui") == EmotionType.SADNESS  # guilt -> sadness


class TestParseBeats:
    """インラインビートパーステスト"""

    @pytest.fixture
    def char_dict(self):
        # Use Unicode escape sequences for Japanese characters
        return {"A", "B", "C", "\u4e3b\u4eba\u516c", "\u30d2\u30ed\u30a4\u30f3"}

    def test_parse_inline_beat_basic(self, char_dict):
        """基本的なタグパース"""
        text = 'A\u300c\u884c\u3050\u305e\u300d\n[beat:fear+0.6 cause="ep14 betrayal"]\nB\u300c\u5f85\u3061\u306a\u3055\u3044\u300d'
        clean, beats = parse_beats(text, episode=15, scene=1, character_dict=char_dict)
        
        assert len(beats) == 1
        beat = beats[0]
        assert beat.episode == 15
        assert beat.scene == 1
        assert beat.emotion.value == "fear"
        assert beat.delta == 0.6
        assert beat.cause == "ep14 betrayal"
        assert beat.confidence == 0.9
        assert "[beat:" not in clean  # タグが除去されている

    def test_parse_multiple_beats_same_line(self, char_dict):
        """同一行に複数タグ"""
        text = '[beat:aff+0.3][beat:ten-0.2] A\u300c\u884c\u304f\u300d'
        clean, beats = parse_beats(text, episode=1, scene=1, character_dict=char_dict)
        
        assert len(beats) == 2
        assert beats[0].emotion.value == "affection"
        assert beats[0].delta == 0.3
        assert beats[1].emotion.value == "tension"
        assert beats[1].delta == -0.2

    def test_parse_negative_delta(self, char_dict):
        """負のdelta"""
        text = 'A\u300c\u4fe1\u7528\u3067\u304d\u306a\u3044\u300d[beat:aff-0.5 cause="betrayal"]'
        clean, beats = parse_beats(text, episode=10, scene=2, character_dict=char_dict)
        
        assert len(beats) == 1
        assert beats[0].delta == -0.5
        assert beats[0].cause == "betrayal"

    def test_parse_hidden_flag(self, char_dict):
        """hiddenフラグ"""
        text = 'A\u300c\u5e73\u6c17\u3060\u300d[beat:fea+0.8 hidden]'
        clean, beats = parse_beats(text, episode=1, scene=1, character_dict=char_dict)
        
        assert len(beats) == 1
        assert beats[0].hidden is True

    def test_parse_no_cause_defaults(self, char_dict):
        """cause省略時のデフォルト"""
        text = 'A\u300c\u884c\u304f\u300d[beat:ten+0.3]'
        clean, beats = parse_beats(text, episode=5, scene=1, character_dict=char_dict)
        
        assert len(beats) == 1
        assert "ep5 inline annotation" in beats[0].cause

    def test_parse_emotion_aliases(self, char_dict):
        """感情エイリアス"""
        text = 'A\u300c\u884c\u304f\u300d[beat:fea+0.5]'
        clean, beats = parse_beats(text, episode=1, scene=1, character_dict=char_dict)
        
        assert len(beats) == 1
        assert beats[0].emotion == EmotionType.FEAR

    def test_speaker_estimation(self, char_dict):
        """発言者推定の動作確認"""
        text = 'A\u300c\u884c\u3050\u305e\u300d\n[beat:fear+0.6]'
        clean, beats = parse_beats(text, episode=1, scene=1, character_dict=char_dict)
        
        assert len(beats) == 1
        assert beats[0].source == "A"

    def test_no_character_dict(self):
        """辞書なしでも動作（空セット）"""
        text = 'A\u300c\u884c\u304f\u300d[beat:fear+0.5]'
        clean, beats = parse_beats(text, episode=1, scene=1, character_dict=set())
        
        # 辞書が空だと推定できないため beats は空
        assert beats == []
        assert "[beat:" not in clean

    def test_clean_text_preserves_non_tag_content(self, char_dict):
        """タグ以外のテキストが保持される"""
        text = 'A\u300c\u884c\u3050\u305e\u300d\n[beat:fear+0.6]\nB\u300c\u5f85\u3061\u306a\u3055\u3044\u300d'
        clean, beats = parse_beats(text, episode=1, scene=1, character_dict=char_dict)
        
        assert 'A\u300c\u884c\u3050\u305e\u300d' in clean
        assert 'B\u300c\u5f85\u3061\u306a\u3055\u3044\u300d' in clean
        assert "[beat:" not in clean