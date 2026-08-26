"""
src/backend/workflows/edges/writing_edges.py - 執筆グラフの条件分岐エッジ
"""

from __future__ import annotations

import logging
from typing import Literal

from src.backend.workflows.state import WritingGraphState

logger = logging.getLogger(__name__)


def check_audit_results(state: WritingGraphState) -> Literal["generate_draft", "__end__"]:
    """
    自己監査結果と反復回数に基づき、再ドラフト生成に進むか、完了とするかを判定する。
    """
    integrity_ok = state.get("is_integrity_ok", True)
    causal_ok = state.get("is_causal_ok", True)
    score = state.get("quality_score", 0.0)
    ac_iter = state.get("ac_iter", 1)
    max_ac_iter = state.get("max_ac_iter", 3)

    logger.info(
        f"[WritingEdge] Check audit: integrity={integrity_ok}, causal={causal_ok}, score={score:.2f}, iter={ac_iter}/{max_ac_iter}"
    )

    # 監査合格、または最大反復回数到達で終了
    if (integrity_ok and causal_ok and score >= 0.75) or ac_iter >= max_ac_iter:
        if ac_iter >= max_ac_iter and not (integrity_ok and causal_ok):
            logger.warning(f"[WritingEdge] Max iterations reached ({ac_iter}). Proceeding to END with current draft.")
        else:
            logger.info("[WritingEdge] Audit passed successfully. Moving to END.")
        return "__end__"

    logger.info("[WritingEdge] Audit failed. Looping back to 'generate_draft' with feedback.")
    return "generate_draft"
