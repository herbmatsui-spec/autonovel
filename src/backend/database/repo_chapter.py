from __future__ import annotations

"""
database/repo_chapter.py - 後方互換性用エイリアス (正本: src.backend.database.repositories.chapter)
"""
from src.backend.database.repositories.chapter import ChapterRepository

ChapterRepositoryMixin = ChapterRepository

__all__ = ["ChapterRepository", "ChapterRepositoryMixin"]
