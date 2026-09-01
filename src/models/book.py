"""AutoNovel の主要ドメインモデル (Book, Chapter, Character, Plot, Bible) - 後方互換 re-export."""
from __future__ import annotations

from src.backend.database.models import Bible, Book, Chapter, Character, Plot

__all__ = ["Book", "Chapter", "Character", "Plot", "Bible"]
