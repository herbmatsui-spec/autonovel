from __future__ import annotations

"""
database/repo_character.py - 後方互換性用エイリアス (正本: src.backend.database.repositories.character)
"""
from src.backend.database.repositories.character import CharacterRepository

CharacterRepositoryMixin = CharacterRepository

__all__ = ["CharacterRepository", "CharacterRepositoryMixin"]
