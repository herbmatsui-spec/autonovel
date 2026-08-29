"""
src/backend/workflows/graphs/review_graph.py - 推敲・品質監査マルチエージェントグラフ (ReviewGraph)
"""

from __future__ import annotations

import functools
import logging
from typing import Any

try:
    from langgraph.graph import END, START, StateGraph
    HAS_LANGGRAPH = True
except ImportError:
    StateGraph = None  # type: ignore
    START = "__start__"  # type: ignore
    END = "__end__"  # type: ignore
    HAS_LANGGRAPH = False

from src.backend.workflows.nodes.review_nodes import (
    analyze_pacing_node,
    check_character_consistency_node,
    propose_edits_node,
    run_review_parallel,
    score_commercial_node,
)
from src.backend.workflows.state import ReviewGraphState

logger = logging.getLogger(__name__)


def create_review_graph(llm_provider: Any = None) -> Any:
    """ReviewGraph の StateGraph を定義して構築する"""
    if not HAS_LANGGRAPH or StateGraph is None:
        logger.warning("[ReviewGraph] LangGraph is not available. Falling back to sequential execution wrapper.")
        return SequentialReviewGraphFallback(llm_provider=llm_provider)

    graph = StateGraph(ReviewGraphState)

    # 依存性注入
    bound_pacing_node = functools.partial(analyze_pacing_node, llm_provider=llm_provider)
    bound_char_node = functools.partial(check_character_consistency_node, llm_provider=llm_provider)
    bound_commercial_node = functools.partial(score_commercial_node, llm_provider=llm_provider)
    bound_propose_node = functools.partial(propose_edits_node, llm_provider=llm_provider)

    # ノード追加
    graph.add_node("analyze_pacing", bound_pacing_node)
    graph.add_node("check_character_consistency", bound_char_node)
    graph.add_node("score_commercial", bound_commercial_node)
    graph.add_node("propose_edits", bound_propose_node)

    # エッジ接続 (Pacing -> Character -> Commercial -> Synthesis)
    graph.add_edge(START, "analyze_pacing")
    graph.add_edge("analyze_pacing", "check_character_consistency")
    graph.add_edge("check_character_consistency", "score_commercial")
    graph.add_edge("score_commercial", "propose_edits")
    graph.add_edge("propose_edits", END)

    return graph


def compile_review_graph(llm_provider: Any = None, checkpointer: Any = None) -> Any:
    """ReviewGraph をコンパイルして実行可能オブジェクトを返す"""
    builder = create_review_graph(llm_provider=llm_provider)
    if hasattr(builder, "compile"):
        return builder.compile(checkpointer=checkpointer)
    return builder


class SequentialReviewGraphFallback:
    """LangGraph 非導入環境用のフォールバック並列/シーケンシャル実行クラス"""

    def __init__(self, llm_provider: Any = None):
        self.llm_provider = llm_provider

    async def ainvoke(self, state: ReviewGraphState) -> ReviewGraphState:
        """非同期で pacing/character を並列実行し、商業スコア採点と総合提案を実行"""
        current_state = dict(state)
        # 話内並列実行 (pacing + character)
        parallel_res = await run_review_parallel(current_state, llm_provider=self.llm_provider)
        current_state.update(parallel_res)

        comm_res = await score_commercial_node(current_state, llm_provider=self.llm_provider)
        current_state.update(comm_res)

        propose_res = await propose_edits_node(current_state, llm_provider=self.llm_provider)
        current_state.update(propose_res)

        return current_state
