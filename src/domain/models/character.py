from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field

from src.domain.types import BookId, CharacterId


class Character(BaseModel):
    """
    Character ドメインエンティティ。
    登場人物の属性と役割を保持する。
    """
    id: CharacterId
    book_id: BookId
    name: str
    role: str
    registry_data: Dict[str, Any] = Field(default_factory=dict)  # JSON形式の属性データ

    def get_attribute(self, key: str, default: Any = None) -> Any:
        """レジストリデータから特定の属性を取得する"""
        return self.registry_data.get(key, default)
