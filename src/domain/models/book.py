from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.domain.types import BookId


@dataclass(frozen=True)
class Book:
    """
    Book ドメインエンティティ。
    DBモデル(src.backend.database.models.Book)とは独立し、ビジネスロジックを保持する。
    """
    id: BookId
    title: str
    genre: str
    concept: str
    synopsis: str
    target_eps: int
    style_dna: str
    marketing_data: str
    cumulative_tension: int = 0
    cumulative_qol: int = 0
    cumulative_cost: float = 0.0
    sanctuary_integrity: int = 100
    current_branch_id: Optional[int] = None
    created_at: Optional[str] = None

    def update_tension(self, delta: int) -> Book:
        """緊張感を更新した新しいBookインスタンスを返す（不変性の維持）"""
        return Book(
            **{**self.__dict__, "cumulative_tension": self.cumulative_tension + delta}
        )

    def update_qol(self, delta: int) -> Book:
        """QOLを更新した新しいBookインスタンスを返す"""
        return Book(
            **{**self.__dict__, "cumulative_qol": self.cumulative_qol + delta}
        )
