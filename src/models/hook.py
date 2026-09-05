from __future__ import annotations

from typing import Literal, Optional
from dataclasses import dataclass


@dataclass
class Hook:
    """フックデータクラス"""
    id: str
    type: Literal["mystery", "threat", "emotion"]
    content: str
    target_position: Literal["episode_end", "volume_end", "series_end"]
    volume: int
    episode: int
    chapter: int

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "type": self.type,
            "content": self.content,
            "target_position": self.target_position,
            "volume": self.volume,
            "episode": self.episode,
            "chapter": self.chapter,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Hook":
        """辞書からインスタンスを生成"""
        return cls(
            id=data["id"],
            type=data["type"],
            content=data["content"],
            target_position=data["target_position"],
            volume=data["volume"],
            episode=data["episode"],
            chapter=data["chapter"],
        )