from __future__ import annotations

"""
database/repo_bible.py - 後方互換性用エイリアス (正本: src.backend.database.repositories.bible)
"""
from src.backend.database.repositories.bible import BibleRepository

BibleRepositoryMixin = BibleRepository

__all__ = ["BibleRepository", "BibleRepositoryMixin"]
