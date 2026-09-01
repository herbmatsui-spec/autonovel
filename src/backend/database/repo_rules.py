from __future__ import annotations

"""
database/repo_rules.py - 後方互換性用エイリアス (正本: src.backend.database.repositories.rules)
"""
from src.backend.database.repositories.rules import RulesRepository

RulesRepositoryMixin = RulesRepository

__all__ = ["RulesRepository", "RulesRepositoryMixin"]
