"""Data models for emotional vector fusion layer."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from src.pipeline.emotional_residue import EmotionalVector, EmotionType


@dataclass
class SourceVector:
    """単一ソース（名前空間）から収集された感情ベクトル情報"""
    namespace: str
    vector: EmotionalVector
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "namespace": self.namespace,
            "vector": self.vector.to_dict(),
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SourceVector:
        return cls(
            namespace=data["namespace"],
            vector=EmotionalVector.from_dict(data["vector"]),
            confidence=float(data["confidence"]),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(timezone.utc),
        )


@dataclass
class FusedValue:
    """融合後の感情値"""
    value: float
    primary_source: str
    contributing_sources: List[str] = field(default_factory=list)
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "value": self.value,
            "primary_source": self.primary_source,
            "contributing_sources": list(self.contributing_sources),
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FusedValue:
        return cls(
            value=float(data["value"]),
            primary_source=str(data["primary_source"]),
            contributing_sources=list(data.get("contributing_sources", [])),
            confidence=float(data.get("confidence", 1.0)),
        )


@dataclass
class Conflict:
    """矛盾情報
    sources: List[Tuple[source_name, value, confidence]]
    """
    pair: Tuple[str, str]
    emotion: EmotionType
    sources: List[Tuple[str, float, float]] = field(default_factory=list)
    conflict_id: str = ""

    def __post_init__(self):
        if not self.conflict_id:
            src_str = "-".join(sorted(s[0] for s in self.sources)) if self.sources else "none"
            self.conflict_id = f"{self.pair[0]}_{self.pair[1]}_{self.emotion.value}_{src_str}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict_id": self.conflict_id,
            "pair": list(self.pair),
            "emotion": self.emotion.value,
            "sources": [list(s) for s in self.sources],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Conflict:
        pair_data = data["pair"]
        pair = (pair_data[0], pair_data[1])
        emotion = EmotionType(data["emotion"])
        sources = [(str(s[0]), float(s[1]), float(s[2])) for s in data.get("sources", [])]
        conflict_id = data.get("conflict_id", "")
        return cls(pair=pair, emotion=emotion, sources=sources, conflict_id=conflict_id)


@dataclass
class FusedVector:
    """全感情値の融合結果および矛盾情報"""
    values: Dict[Tuple[str, str, EmotionType], FusedValue] = field(default_factory=dict)
    conflicts: List[Conflict] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_value(self, source: str, target: str, emotion: EmotionType) -> Optional[FusedValue]:
        return self.values.get((source, target, emotion))

    def to_dict(self) -> Dict[str, Any]:
        serialized_values = {}
        for (src, tgt, emo), f_val in self.values.items():
            key = f"{src}->{tgt}:{emo.value}"
            serialized_values[key] = f_val.to_dict()

        return {
            "values": serialized_values,
            "conflicts": [c.to_dict() for c in self.conflicts],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FusedVector:
        values: Dict[Tuple[str, str, EmotionType], FusedValue] = {}
        for key, val_dict in data.get("values", {}).items():
            # key format: "A->B:emotion"
            if "->" in key and ":" in key:
                pair_part, emo_part = key.split(":", 1)
                src, tgt = pair_part.split("->", 1)
                emotion = EmotionType(emo_part)
                values[(src, tgt, emotion)] = FusedValue.from_dict(val_dict)

        conflicts = [Conflict.from_dict(c) for c in data.get("conflicts", [])]
        metadata = dict(data.get("metadata", {}))
        return cls(values=values, conflicts=conflicts, metadata=metadata)
