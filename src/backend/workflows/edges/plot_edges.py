"""
src/backend/workflows/edges/plot_edges.py - プロット生成グラフの条件分岐エッジ
"""

from __future__ import annotations

import logging
from typing import Literal

from src.backend.workflows.state import PlotGraphState

logger = logging.getLogger(__name__)


def should_refine_plot(state: PlotGraphState) -> Literal["refine_plot", "__end__"]:
    """
    評価結果とイテレーション回数に基づき、改善（再推敲）に進むか、完了とするかを判定する。
    """
    is_approved = state.get("is_approved", False)
    score = state.get("quality_score", 0.0)
    current_iter = state.get("current_iteration", 1)
    max_iter = state.get("max_iterations", 3)

    logger.info(
        f"[PlotEdge] Check condition: is_approved={is_approved}, score={score:.2f}, iter={current_iter}/{max_iter}"
    )

    # 合格基準を満たしている、または最大試行回数に到達した場合は終了
    if is_approved or score >= 0.85:
        logger.info("[PlotEdge] Plot approved. Moving to END.")
        return "__end__"

    if current_iter >= max_iter:
        logger.warning(f"[PlotEdge] Max iterations reached ({current_iter}). Forcing completion to END.")
        return "__end__"

    logger.info("[PlotEdge] Quality threshold not met. Looping back to 'refine_plot'.")
    return "refine_plot"
