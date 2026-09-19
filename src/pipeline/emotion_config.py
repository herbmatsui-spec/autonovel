"""Emotion lexicon and pattern configuration loader."""
from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml

from src.pipeline.emotional_residue import EmotionType


@functools.lru_cache(maxsize=1)
def _load_raw_config() -> dict[str, Any]:
    """YAML設定を読み込み（キャッシュ付き）"""
    config_path = Path(__file__).parent.parent.parent / "config" / "emotion_lexicon.yaml"
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class EmotionLexicon:
    """感情語彙辞書・パターン保持クラス"""
    
    def __init__(self, raw_config: dict[str, Any]):
        self.lexicon: dict[str, dict[str, list[str]]] = raw_config["emotion_lexicon"]
        self.dependency_patterns: list[list] = raw_config["dependency_patterns"]
        self.polarity_flip_verbs: list[str] = raw_config["polarity_flip_verbs"]
        self.intensifiers: list[str] = raw_config["intensifiers"]
        self.attenuators: list[str] = raw_config["attenuators"]
        
        # 感情タイプ検証
        expected_types = {e.value for e in EmotionType}
        actual_types = set(self.lexicon.keys())
        if actual_types != expected_types:
            raise ValueError(f"Lexicon keys mismatch. Expected: {expected_types}, Got: {actual_types}")

    def get_positive_words(self, emotion_type: str) -> list[str]:
        """正の語彙リスト取得"""
        return self.lexicon.get(emotion_type, {}).get("positive", [])

    def get_negative_words(self, emotion_type: str) -> list[str]:
        """負の語彙リスト取得"""
        return self.lexicon.get(emotion_type, {}).get("negative", [])

    def get_all_words(self, emotion_type: str) -> list[str]:
        """全語彙取得（正＋負）"""
        pos = self.get_positive_words(emotion_type)
        neg = self.get_negative_words(emotion_type)
        return pos + neg


@functools.lru_cache(maxsize=1)
def load_emotion_lexicon() -> EmotionLexicon:
    """感情辞書をロード（シングルトン）"""
    raw = _load_raw_config()
    return EmotionLexicon(raw)


@functools.lru_cache(maxsize=1)
def load_dependency_patterns() -> list[list]:
    """依存構造パターンをロード（シングルトン）"""
    raw = _load_raw_config()
    return raw["dependency_patterns"]


def get_polarity_flip_verbs() -> list[str]:
    """極性反転動詞リスト取得"""
    return load_emotion_lexicon().polarity_flip_verbs


def get_intensifiers() -> list[str]:
    """増幅修飾語リスト取得"""
    return load_emotion_lexicon().intensifiers


def get_attenuators() -> list[str]:
    """減衰修飾語リスト取得"""
    return load_emotion_lexicon().attenuators


__all__ = [
    "EmotionLexicon",
    "load_emotion_lexicon",
    "load_dependency_patterns",
    "get_polarity_flip_verbs",
    "get_intensifiers",
    "get_attenuators",
]