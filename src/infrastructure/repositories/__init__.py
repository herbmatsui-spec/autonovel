"""下位互換性維持のためのエイリアス。実体は src.infrastructure.repositories に移動しました。"""
from __future__ import annotations
import importlib
import sys


def __getattr__(name: str):
    _module_map = {
        "AuditRepository": "audit",
        "BaseRepository": "base",
        "BibleRepository": "bible",
        "BookRepository": "book",
        "BookScoreRepository": "book_score",
        "BranchRepository": "branch",
        "ChapterRepository": "chapter",
        "CharacterRepository": "character",
        "CollabRepository": "collab",
        "CostRepository": "cost",
        "EasyModeDraftRepository": "easy_mode_draft_repository",
        "IllustrationRepository": "illustration",
        "MiscRepository": "misc",
        "NarrativeMetricRepository": "narrative_metrics_repo",
        "PDCAHistoryRepository": "pdca_history",
        "PlotRepository": "plot",
        "RulesRepository": "rules",
        "TraceRepository": "trace",
        "PromptVersionRepository": "prompt_versions",
        "PromptMetricsRepository": "repo_prompt_metrics",
    }
    if name in _module_map:
        module_name = _module_map[name]
        module = importlib.import_module(f".{module_name}", __package__)
        return getattr(module, name)
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


def __dir__():
    return list(_module_map.keys())


__all__ = [
    "AuditRepository",
    "BaseRepository",
    "BibleRepository",
    "BookRepository",
    "BookScoreRepository",
    "BranchRepository",
    "ChapterRepository",
    "CharacterRepository",
    "CollabRepository",
    "CostRepository",
    "EarlyModeDraftRepository",
    "IllustrationRepository",
    "MiscRepository",
    "NarrativeMetricRepository",
    "PDCAHistoryRepository",
    "PlotRepository",
    "RulesRepository",
    "TraceRepository",
    "PromptVersionRepository",
    "PromptMetricsRepository",
]