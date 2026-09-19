"""Emotional beat annotation data structures."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional
from uuid import uuid4

from src.pipeline.emotional_residue import EmotionalSignal, EmotionType


@dataclass
class EmotionalBeat:
    """感情ビートアノテーション（作者が明示的に記述）"""
    episode: int
    scene: int
    source: str
    target: str
    emotion: EmotionType
    delta: float                    # -1.0 ~ +1.0 (変化量)
    cause: str                      # 理由・根拠
    beat_id: str = field(default_factory=lambda: str(uuid4())[:8])
    confidence: float = 1.0         # 確信度 0.0~1.0
    hidden: bool = False            # 表向き/内心の区別
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        # 値のクランプ（バリデーション後のため、ここでは警告のみ）
        self.delta = max(-1.0, min(1.0, self.delta))
        self.confidence = max(0.0, min(1.0, self.confidence))
        
        # 基本バリデーション
        if not self.source or not self.target:
            raise ValueError("source and target must not be empty")
        # causeは空でも許可（バリデーターで警告）

    def to_signal(self) -> EmotionalSignal:
        """Week 1互換のEmotionalSignalに変換"""
        return EmotionalSignal(
            source=self.source,
            target=self.target,
            emotion_type=self.emotion,
            value=self.delta,
            confidence=self.confidence,
            evidence_span=f"[beat:{self.emotion.value}{self.delta:+.1f} cause=\"{self.cause}\"]",
            episode_id=f"ep{self.episode}",
            cause=self.cause,
            hidden=self.hidden,
        )

    @classmethod
    def from_dict(cls, data: dict, episode: int, scene: int) -> EmotionalBeat:
        """辞書から構築（フロントマター用）"""
        return cls(
            episode=episode,
            scene=scene,
            source=data["source"],
            target=data["target"],
            emotion=EmotionType(data["emotion"]),
            delta=float(data["delta"]),
            cause=data["cause"],
            beat_id=data.get("beat_id", str(uuid4())[:8]),
            confidence=float(data.get("confidence", 1.0)),
            hidden=bool(data.get("hidden", False)),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> dict:
        """辞書に変換（フロントマター用）"""
        return {
            "beat_id": self.beat_id,
            "source": self.source,
            "target": self.target,
            "emotion": self.emotion.value,
            "delta": self.delta,
            "cause": self.cause,
            "confidence": self.confidence,
            "hidden": self.hidden,
            "metadata": self.metadata,
        }


@dataclass
class ParsedScript:
    """パース結果"""
    clean_text: str
    beats: list[EmotionalBeat]
    frontmatter_beats: list[EmotionalBeat]
    inline_beats: list[EmotionalBeat]


__all__ = ["EmotionalBeat", "ParsedScript"]