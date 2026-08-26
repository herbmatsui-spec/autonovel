"""
src/backend/workflows/graphs/review_graph.py - 推敲・品質監査マルチエージェントグラフ (ReviewGraph)
"""

from __future__ import annotations

import functools
import logging
from typing import Any, Optional

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
    bound_propose_node = functools.partial(propose_edits_node, llm_provider=llm_provider)

    # ノード追加
    graph.add_node("analyze_pacing", bound_pacing_node)
    graph.add_node("check_character_consistency", bound_char_node)
    graph.add_node("propose_edits", bound_propose_node)

    # エッジ接続 (Pacing -> Character -> Synthesis)
    graph.add_edge(START, "analyze_pacing")
    graph.add_edge("analyze_pacing", "check_character_consistency")
    graph.add_edge("check_character_consistency", "propose_edits")
    graph.add_edge("propose_edits", END)

    return graph


def compile_review_graph(llm_provider: Any = None, checkpointer: Any = None) -> Any:
    """ReviewGraph をコンパイルして実行可能オブジェクトを返す"""
    builder = create_review_graph(llm_provider=llm_provider)
    if hasattr(builder, "compile"):
        return builder.compile(checkpointer=checkpointer)
    return builder


class SequentialReviewGraphFallback:
    """LangGraph 非導入環境用のフォールバックシーケンシャル実行クラス"""

    def __init__(self, llm_provider: Any = None):
        self.llm_provider = llm_provider

    async def ainvoke(self, state: ReviewGraphState) -> ReviewGraphState:
        """非同期でノードを実行して推敲監査パイプラインをエミュレート"""
        current_state = dict(state)
        pacing_res = await analyze_pacing_node(current_state, llm_provider=self.llm_provider)
        current_state.update(pacing_res)

        char_res = await check_character_consistency_node(current_state, llm_provider=self.llm_provider)
        current_state.update(char_res)

        propose_res = await propose_edits_node(current_state, llm_provider=self.llm_provider)
        current_state.update(propose_res)

        return current_state
