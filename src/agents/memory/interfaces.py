"""Interfaces and data structures for 3-tier hierarchical agent memory."""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class MemoryEntry:
    """Archival Memory に格納される長期記憶エントリ"""
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "embedding": self.embedding,
            "metadata": dict(self.metadata),
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryEntry:
        ts = datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(timezone.utc)
        return cls(
            id=str(data["id"]),
            content=str(data["content"]),
            embedding=data.get("embedding"),
            metadata=dict(data.get("metadata", {})),
            timestamp=ts,
        )


@dataclass
class WorkingFrame:
    """Working Memory 内のシーン単位揮発フレーム"""
    scene_id: int
    emotional_beats: List[Dict[str, Any]] = field(default_factory=list)
    plot_points: List[str] = field(default_factory=list)
    context_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "emotional_beats": list(self.emotional_beats),
            "plot_points": list(self.plot_points),
            "context_summary": self.context_summary,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> WorkingFrame:
        return cls(
            scene_id=int(data["scene_id"]),
            emotional_beats=list(data.get("emotional_beats", [])),
            plot_points=list(data.get("plot_points", [])),
            context_summary=str(data.get("context_summary", "")),
        )


class MemoryBlock(abc.ABC):
    """単一メモリブロックの基底抽象クラス"""

    @abc.abstractmethod
    def read(self) -> str:
        """メモリ内容の読み出し"""
        ...

    @abc.abstractmethod
    def write(self, content: str) -> None:
        """メモリ内容の書き込み"""
        ...

    @abc.abstractmethod
    def size(self) -> int:
        """メモリサイズの推定"""
        ...


class BaseCoreMemory(abc.ABC):
    """常駐CoreMemoryのインターフェース"""

    @abc.abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        ...

    @abc.abstractmethod
    def set(self, key: str, value: Any) -> None:
        ...

    @abc.abstractmethod
    def dump(self) -> Dict[str, Any]:
        ...


class BaseArchivalMemory(abc.ABC):
    """外部ArchivalMemoryのインターフェース"""

    @abc.abstractmethod
    def search(self, query: str, k: int = 5) -> List[MemoryEntry]:
        ...

    @abc.abstractmethod
    def insert(self, entry: MemoryEntry) -> None:
        ...

    @abc.abstractmethod
    def delete(self, entry_id: str) -> bool:
        ...


class BaseWorkingMemory(abc.ABC):
    """シーン単位WorkingMemoryのインターフェース"""

    @abc.abstractmethod
    def push(self, frame: WorkingFrame) -> None:
        ...

    @abc.abstractmethod
    def pop(self) -> Optional[WorkingFrame]:
        ...

    @abc.abstractmethod
    def peek(self) -> Optional[WorkingFrame]:
        ...


__all__ = [
    "MemoryEntry",
    "WorkingFrame",
    "MemoryBlock",
    "BaseCoreMemory",
    "BaseArchivalMemory",
    "BaseWorkingMemory",
]
