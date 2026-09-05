from __future__ import annotations

from typing import Literal, Optional
from dataclasses import dataclass


@dataclass
class Foreshadowing:
    """伏線データクラス"""
    id: str
    content: str
    hang_volume: int
    hang_episode: int
    hang_chapter: int
    hang_type: Literal["explicit", "implicit", "reader_task", "unresolved"]
    importance: Literal["★", "★★", "★★★"]
    resolution_volume: Optional[int] = None
    resolution_episode: Optional[int] = None

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "content": self.content,
            "hang_volume": self.hang_volume,
            "hang_episode": self.hang_episode,
            "hang_chapter": self.hang_chapter,
            "hang_type": self.hang_type,
            "importance": self.importance,
            "resolution_volume": self.resolution_volume,
            "resolution_episode": self.resolution_episode,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Foreshadowing":
        """辞書からインスタンスを生成"""
        return cls(
            id=data["id"],
            content=data["content"],
            hang_volume=data["hang_volume"],
            hang_episode=data["hang_episode"],
            hang_chapter=data["hang_chapter"],
            hang_type=data["hang_type"],
            importance=data["importance"],
            resolution_volume=data.get("resolution_volume"),
            resolution_episode=data.get("resolution_episode"),
        )