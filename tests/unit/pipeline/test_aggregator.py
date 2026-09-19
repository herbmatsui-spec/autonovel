"""Tests for signal aggregator."""
from __future__ import annotations

import pytest

from src.pipeline.emotional_residue import EmotionalSignal, EmotionalVector, EmotionType
from src.pipeline.aggregator import (
    aggregate_signals,
    merge_vectors,
    get_dominant_emotion,
    get_emotional_summary,
)


class TestAggregator:
    """シグナル集約テスト"""

    def test_aggregate_multiple_signals(self):
        """複数シグナルの重み付き平均集約"""
        signals = [
            EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.8, 0.6, "...", "ep01"),
            EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.2, 0.9, "...", "ep01"),
        ]
        
        vector = aggregate_signals(signals)
        
        # 重み付き平均: (0.8*0.6 + 0.2*0.9) / 1.5 = 0.66 / 1.5 = 0.44
        expected = (0.8 * 0.6 + 0.2 * 0.9) / 1.5
        assert abs(vector.get_value("A", "B", EmotionType.AFFECTION) - expected) < 0.01
        assert vector.get_confidence("A", "B", EmotionType.AFFECTION) == 1.0

    def test_aggregate_different_emotions(self):
        """異なる感情タイプの集約"""
        signals = [
            EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.5, 0.8, "...", "ep01"),
            EmotionalSignal("A", "B", EmotionType.TENSION, 0.7, 0.6, "...", "ep01"),
            EmotionalSignal("B", "A", EmotionType.FEAR, 0.3, 0.7, "...", "ep01"),
        ]
        
        vector = aggregate_signals(signals)
        
        assert vector.get_value("A", "B", EmotionType.AFFECTION) == 0.5
        assert vector.get_value("A", "B", EmotionType.TENSION) == 0.7
        assert vector.get_value("B", "A", EmotionType.FEAR) == 0.3

    def test_aggregate_empty(self):
        """空リストの集約"""
        vector = aggregate_signals([])
        assert vector.episode_id == "unknown"
        assert len(vector.signals) == 0

    def test_merge_vectors(self):
        """複数ベクトルのマージ"""
        vec1 = EmotionalVector(episode_id="ep01")
        vec1.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.5, 0.8, "...", "ep01"))
        
        vec2 = EmotionalVector(episode_id="ep02")
        vec2.set_signal(EmotionalSignal("A", "B", EmotionType.TENSION, 0.7, 0.6, "...", "ep02"))
        
        merged = merge_vectors([vec1, vec2])
        
        assert merged.get_value("A", "B", EmotionType.AFFECTION) == 0.5
        assert merged.get_value("A", "B", EmotionType.TENSION) == 0.7

    def test_get_dominant_emotion(self):
        """優勢感情取得"""
        vec = EmotionalVector(episode_id="ep01")
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.3, 0.8, "...", "ep01"))
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.TENSION, 0.8, 0.6, "...", "ep01"))
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.FEAR, -0.5, 0.7, "...", "ep01"))
        
        dominant = get_dominant_emotion(vec, "A", "B")
        
        assert dominant is not None
        assert dominant[0] == EmotionType.TENSION  # 絶対値最大
        assert dominant[1] == 0.8

    def test_get_dominant_emotion_none(self):
        """感情なしペア"""
        vec = EmotionalVector(episode_id="ep01")
        dominant = get_dominant_emotion(vec, "A", "B")
        assert dominant is None

    def test_get_emotional_summary(self):
        """感情サマリ生成"""
        vec = EmotionalVector(episode_id="ep01")
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.AFFECTION, 0.5, 0.8, "...", "ep01"))
        vec.set_signal(EmotionalSignal("A", "B", EmotionType.TENSION, 0.8, 0.6, "...", "ep01"))
        vec.set_signal(EmotionalSignal("C", "D", EmotionType.FEAR, 0.1, 0.5, "...", "ep01"))  # 閾値未満
        
        summary = get_emotional_summary(vec, top_n=2)
        
        assert len(summary) == 2
        # C->Dは閾値0.1未満なのでemotionsが空、またはエントリ自体が除外される可能性
        # 実装では微小値はemotionsから除外されるがエントリは残る
        pair_keys = [(e["source"], e["target"]) for e in summary]
        assert ("A", "B") in pair_keys
        
        # dominantチェック
        ab_entry = next(e for e in summary if e["source"] == "A" and e["target"] == "B")
        assert ab_entry["dominant"] is not None
        assert ab_entry["dominant"]["emotion"] == "tension"

    def test_value_clamping_in_aggregate(self):
        """集約時の値クランプ"""
        signals = [
            EmotionalSignal("A", "B", EmotionType.AFFECTION, 1.5, 0.8, "...", "ep01"),  # クランプ済み
        ]
        vector = aggregate_signals(signals)
        assert vector.get_value("A", "B", EmotionType.AFFECTION) == 1.0