from __future__ import annotations

"""
database/repo_plot.py - 後方互換性用エイリアス (正本: src.backend.database.repositories.plot)
"""
from src.backend.database.repositories.plot import PlotRepository

PlotRepositoryMixin = PlotRepository

__all__ = ["PlotRepository", "PlotRepositoryMixin"]
