"""Signal aggregation and normalization."""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from src.pipeline.emotional_residue import EmotionalSignal, EmotionalVector, EmotionType


def aggregate_signals(signals: list[EmotionalSignal]) -> EmotionalVector:
    """複数シグナルを集約してEmotionalVector生成
    
    同一(source, target, emotion)の重み付き平均（confidence重み）でマージ。
    値は -1.0~1.0 にクランプ。
    """
    if not signals:
        return EmotionalVector(episode_id="unknown")
    
    # エピソードIDは最初のシグナルから取得
    episode_id = signals[0].episode_id
    
    vector = EmotionalVector(episode_id=episode_id)
    
    # 一時的に全シグナルを追加（EmotionalVector.set_signalが重み付き平均を行う）
    for signal in signals:
        vector.set_signal(signal)
    
    return vector


def merge_vectors(vectors: list[EmotionalVector]) -> EmotionalVector:
    """複数のEmotionalVectorをマージ"""
    if not vectors:
        return EmotionalVector(episode_id="unknown")
    
    merged = EmotionalVector(episode_id=vectors[0].episode_id)
    
    for vec in vectors:
        for (source, target, emotion), value in vec.signals.items():
            confidence = vec.confidences.get((source, target, emotion), 0.5)
            cause = vec.causes.get((source, target, emotion))
            
            signal = EmotionalSignal(
                source=source,
                target=target,
                emotion_type=emotion,
                value=value,
                confidence=confidence,
                evidence_span="merged",
                episode_id=vec.episode_id,
                cause=cause,
            )
            merged.set_signal(signal)
    
    return merged


def normalize_vector(vector: EmotionalVector) -> EmotionalVector:
    """ベクトル正規化（極端な値のクリッピング等）"""
    # 現在の実装では set_signal 内でクランプ済み
    # 将来的にL2正規化等を追加する場合はここで実装
    return vector


def get_dominant_emotion(vector: EmotionalVector, source: str, target: str) -> Optional[tuple[EmotionType, float]]:
    """ペア間で最も強い感情を取得"""
    pair_emotions = vector.get_pair_emotions(source, target)
    if not pair_emotions:
        return None
    
    dominant = max(pair_emotions.items(), key=lambda x: abs(x[1]))
    return dominant


def get_emotional_summary(vector: EmotionalVector, top_n: int = 5) -> list[dict]:
    """感情サマリ生成（プロンプト用）"""
    top_pairs = vector.get_top_pairs(top_n)
    summary = []
    
    for (source, target), emotions in top_pairs:
        entry = {
            "source": source,
            "target": target,
            "emotions": {
                emo.value: round(val, 2)
                for emo, val in emotions.items()
                if abs(val) > 0.1  # 微小値は除外
            },
            "dominant": None,
        }
        dom = get_dominant_emotion(vector, source, target)
        if dom:
            entry["dominant"] = {"emotion": dom[0].value, "value": round(dom[1], 2)}
        summary.append(entry)
    
    return summary


__all__ = [
    "aggregate_signals",
    "merge_vectors",
    "normalize_vector",
    "get_dominant_emotion",
    "get_emotional_summary",
]