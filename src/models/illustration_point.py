from __future__ import annotations

from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class IllustrationPoint:
    """挿絵ポイントデータクラス"""
    id: str
    page: str  # 例: "口絵1", "15"
    scene_description: str
    composition: str
    props: str
    expressions: Dict[str, str]  # キャラ名 -> 表情説明
    background: str
    notes: Optional[str] = None

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "id": self.id,
            "page": self.page,
            "scene_description": self.scene_description,
            "composition": self.composition,
            "props": self.props,
            "expressions": self.expressions,
            "background": self.background,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "IllustrationPoint":
        """辞書からインスタンスを生成"""
        return cls(
            id=data["id"],
            page=data["page"],
            scene_description=data["scene_description"],
            composition=data["composition"],
            props=data["props"],
            expressions=data["expressions"],
            background=data["background"],
            notes=data.get("notes"),
        )