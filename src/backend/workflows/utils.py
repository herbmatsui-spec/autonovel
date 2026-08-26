"""
src/backend/workflows/utils.py - ワークフロー共通ユーティリティ関数群
"""

from __future__ import annotations

import asyncio
import logging
import random
from typing import Any, Callable, Dict, List, Optional, TypeVar

from src.core.exceptions import LLMTemporaryError


logger = logging.getLogger(__name__)

T = TypeVar("T")


async def with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 30.0,
    **kwargs: Any,
) -> Any:
    """
    一時的なLLMエラーに対して指数バックオフとジッター付きで非同期関数をリトライ実行する。
    """
    delay = initial_delay
    last_exception = None

    for attempt in range(1, max_retries + 1):
        try:
            return await func(*args, **kwargs)
        except LLMTemporaryError as e:
            last_exception = e
            if attempt == max_retries:
                logger.error(f"[Workflow Retry] Max retries ({max_retries}) reached for {func.__name__}: {e}")
                raise
            jitter = random.uniform(0.8, 1.2)
            sleep_time = min(delay * jitter, max_delay)
            logger.warning(
                f"[Workflow Retry] Attempt {attempt}/{max_retries} failed for {func.__name__}: {e}. Retrying in {sleep_time:.2f}s..."
            )
            await asyncio.sleep(sleep_time)
            delay *= backoff_factor
        except Exception as e:
            logger.error(f"[Workflow Unrecoverable Error] in {func.__name__}: {e}")
            raise

    if last_exception:
        raise last_exception


def format_critique_feedback(issues: List[Dict[str, Any]], suggestions: Optional[List[str]] = None) -> str:
    """ノード間のフィードバック指示文をプロンプト用に整形する"""
    feedback_lines = []
    if issues:
        feedback_lines.append("【検出された改善課題】")
        for i, issue in enumerate(issues, 1):
            category = issue.get("category", "General")
            desc = issue.get("description", issue.get("reason", str(issue)))
            feedback_lines.append(f"{i}. [{category}] {desc}")

    if suggestions:
        feedback_lines.append("\n【修正・改善の推奨方針】")
        for i, sug in enumerate(suggestions, 1):
            feedback_lines.append(f"{i}. {sug}")

    return "\n".join(feedback_lines)


def calculate_quality_score(
    integrity_ok: bool,
    causal_ok: bool,
    issue_count: int,
    base_score: float = 1.0,
) -> float:
    """監査結果に基づく品質スコア (0.0 - 1.0) の計算"""
    score = base_score
    if not integrity_ok:
        score -= 0.3
    if not causal_ok:
        score -= 0.3
    score -= min(issue_count * 0.1, 0.4)
    return max(0.0, min(1.0, score))
