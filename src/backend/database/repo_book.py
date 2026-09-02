from __future__ import annotations

"""
database/repo_book.py - 後方互換性用エイリアス (正本: src.backend.database.repositories.book)
"""
from src.backend.database.repositories.book import BookRepository

BookRepositoryMixin = BookRepository

__all__ = ["BookRepository", "BookRepositoryMixin"]
