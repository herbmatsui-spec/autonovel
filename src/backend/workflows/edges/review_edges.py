"""
src/backend/workflows/edges/review_edges.py - 推敲・レビューグラフの条件分岐エッジ
"""

from __future__ import annotations

import logging
from typing import Literal

from src.backend.workflows.state import ReviewGraphState

logger = logging.getLogger(__name__)


def requires_revision_edge(state: ReviewGraphState) -> Literal["__end__"]:
    """
    推敲結果の判定（MasterGraph または WritingGraph に結果を返却するため、現状は合成後に END へ合流）
    """
    req_rev = state.get("requires_revision", False)
    logger.info(f"[ReviewEdge] Review concluded. Requires revision={req_rev}. Finalizing to END.")
    return "__end__"
