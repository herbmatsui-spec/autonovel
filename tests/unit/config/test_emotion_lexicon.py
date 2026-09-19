"""Tests for emotion lexicon configuration."""
from __future__ import annotations

import pytest
import yaml

from src.pipeline.emotion_config import load_emotion_lexicon, load_dependency_patterns, EmotionLexicon


class TestEmotionLexicon:
    """感情辞書の読み込みテスト"""

    def test_lexicon_loads_correctly(self):
        lexicon = load_emotion_lexicon()
        assert isinstance(lexicon, EmotionLexicon)
        
        # 全感情タイプが存在すること
        expected_emotions = {
            "affection", "tension", "fear", "trust", "intimacy",
            "jealousy", "anger", "sadness", "surprise", "disgust"
        }
        assert set(lexicon.lexicon.keys()) == expected_emotions
        
        # 各感情に positive/negative があること
        for emo_type, lex in lexicon.lexicon.items():
            assert "positive" in lex
            assert "negative" in lex
            assert isinstance(lex["positive"], list)
            assert isinstance(lex["negative"], list)
            assert len(lex["positive"]) > 0
            assert len(lex["negative"]) > 0

    def test_dependency_patterns_load(self):
        patterns = load_dependency_patterns()
        assert isinstance(patterns, list)
        assert len(patterns) > 0
        
        # パターン構造: [subj_dep, obj_dep, emotion_type, weight]
        for pattern in patterns:
            assert len(pattern) == 4
            assert isinstance(pattern[0], str)  # subj_dep
            assert isinstance(pattern[1], str)  # obj_dep
            assert pattern[2] in {
                "affection", "tension", "fear", "trust", "intimacy",
                "jealousy", "anger", "sadness", "surprise", "disgust"
            }
            assert isinstance(pattern[3], (int, float))

    def test_polarity_flip_verbs_load(self):
        lexicon = load_emotion_lexicon()
        assert hasattr(lexicon, 'polarity_flip_verbs')
        assert isinstance(lexicon.polarity_flip_verbs, list)
        assert "裏切る" in lexicon.polarity_flip_verbs
        assert "騙す" in lexicon.polarity_flip_verbs

    def test_intensifiers_attenuators_load(self):
        lexicon = load_emotion_lexicon()
        assert hasattr(lexicon, 'intensifiers')
        assert hasattr(lexicon, 'attenuators')
        assert isinstance(lexicon.intensifiers, list)
        assert isinstance(lexicon.attenuators, list)
        assert "底知れぬ" in lexicon.intensifiers
        assert "少し" in lexicon.attenuators

    def test_singleton_behavior(self):
        """シングルトンパターンでキャッシュされること"""
        lexicon1 = load_emotion_lexicon()
        lexicon2 = load_emotion_lexicon()
        assert lexicon1 is lexicon2
        
        patterns1 = load_dependency_patterns()
        patterns2 = load_dependency_patterns()
        assert patterns1 is patterns2

    def test_yaml_file_exists_and_valid(self):
        """YAMLファイルが存在し、正しくパースできること"""
        with open("config/emotion_lexicon.yaml", "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        assert "emotion_lexicon" in data
        assert "dependency_patterns" in data
        assert "polarity_flip_verbs" in data
        assert "intensifiers" in data
        assert "attenuators" in data