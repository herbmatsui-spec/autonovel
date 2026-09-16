"""BookScore のデータクラスとリポジトリプロトコル定義"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

from src.infrastructure.database.models.book_score import BookScore as BookScoreModel


@dataclass
class BookScore:
    overall_score: float
    structure_score: float
    coherency_score: float
    factual_grounding_score: float
    visual_textual_synergy_score: float
    reader_experience_score: float
    specialist_breakdown: Optional[Dict[str, Any]] = None

    def lowest_dimension(self) -> str:
        """Return the lowest scoring dimension."""
        dims = {
            "structure_score": self.structure_score,
            "coherency_score": self.coherency_score,
            "factual_grounding_score": self.factual_grounding_score,
            "visual_textual_synergy_score": self.visual_textual_synergy_score,
            "reader_experience_score": self.reader_experience_score,
        }
        return min(dims, key=dims.get)


class BookScoreRepository(Protocol):
    """BookScore リポジトリのプロトコル"""

    async def save(self, score: BookScoreModel) -> None: ...

    async def get_latest(self, book_id: int, chapter_number: int) -> Optional[BookScoreModel]: ...

    async def get_all_for_book(self, book_id: int) -> list[BookScoreModel]: ...
