from __future__ import annotations

"""
database/repo_misc.py - 後方互換性用エイリアス (正本: src.backend.database.repositories.misc)
"""
from src.backend.database.repositories.misc import MiscRepository

MiscRepositoryMixin = MiscRepository

__all__ = ["MiscRepository", "MiscRepositoryMixin"]
