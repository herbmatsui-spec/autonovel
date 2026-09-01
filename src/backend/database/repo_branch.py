from __future__ import annotations

"""
database/repo_branch.py - 後方互換性用エイリアス (正本: src.backend.database.repositories.branch)
"""
from src.backend.database.repositories.branch import BranchRepository

BranchRepositoryMixin = BranchRepository

__all__ = ["BranchRepository", "BranchRepositoryMixin"]
