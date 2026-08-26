"""
database/repositories/repo_prompt_metrics.py - 後方互換ラッパー

新規コードでは prompt_metrics.py を使用してください。
"""

from src.backend.database.repositories.prompt_metrics import PromptMetricsRepository

__all__ = ["PromptMetricsRepository"]
