"""
src/backend/workflows/graphs/master_graph.py - 全体統括マスターオーケストレーター (MasterGraph)
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

from src.backend.workflows.nodes.master_nodes import (
    call_plot_graph_node,
    call_review_graph_node,
    call_writing_graph_node,
)
from src.backend.workflows.state import MasterGraphState

logger = logging.getLogger(__name__)


def create_master_graph(
    llm_provider: Any = None,
    writing_agent: Any = None,
    reporter: Any = None,
) -> Any:
    """MasterGraph の StateGraph を定義して構築する"""
    if not HAS_LANGGRAPH or StateGraph is None:
        logger.warning("[MasterGraph] LangGraph is not available. Falling back to sequential execution wrapper.")
        return SequentialMasterGraphFallback(
            llm_provider=llm_provider,
            writing_agent=writing_agent,
            reporter=reporter,
        )

    graph = StateGraph(MasterGraphState)

    # 依存性注入
    bound_plot = functools.partial(call_plot_graph_node, llm_provider=llm_provider, reporter=reporter)
    bound_writing = functools.partial(
        call_writing_graph_node,
        llm_provider=llm_provider,
        writing_agent=writing_agent,
        reporter=reporter,
    )
    bound_review = functools.partial(call_review_graph_node, llm_provider=llm_provider, reporter=reporter)

    # ノード追加
    graph.add_node("plot_phase", bound_plot)
    graph.add_node("writing_phase", bound_writing)
    graph.add_node("review_phase", bound_review)

    # エッジ接続 (フルオートシーケンス: Plot -> Writing -> Review -> END)
    graph.add_edge(START, "plot_phase")
    graph.add_edge("plot_phase", "writing_phase")
    graph.add_edge("writing_phase", "review_phase")
    graph.add_edge("review_phase", END)

    return graph


def compile_master_graph(
    llm_provider: Any = None,
    writing_agent: Any = None,
    reporter: Any = None,
    checkpointer: Any = None,
) -> Any:
    """MasterGraph をコンパイルして実行可能オブジェクトを返す"""
    builder = create_master_graph(
        llm_provider=llm_provider,
        writing_agent=writing_agent,
        reporter=reporter,
    )
    if hasattr(builder, "compile"):
        return builder.compile(checkpointer=checkpointer)
    return builder


class SequentialMasterGraphFallback:
    """LangGraph 非導入環境用のフォールバックシーケンシャル実行クラス"""

    def __init__(
        self,
        llm_provider: Any = None,
        writing_agent: Any = None,
        reporter: Any = None,
    ):
        self.llm_provider = llm_provider
        self.writing_agent = writing_agent
        self.reporter = reporter

    async def ainvoke(self, state: MasterGraphState) -> MasterGraphState:
        """非同期でサブグラフノードを逐次実行"""
        current_state = dict(state)
        mode = current_state.get("mode", "full_pipeline")

        if mode in ("full_pipeline", "plot_only"):
            plot_res = await call_plot_graph_node(
                current_state,
                llm_provider=self.llm_provider,
                reporter=self.reporter,
            )
            current_state.update(plot_res)

        if mode in ("full_pipeline", "writing_batch"):
            writing_res = await call_writing_graph_node(
                current_state,
                llm_provider=self.llm_provider,
                writing_agent=self.writing_agent,
                reporter=self.reporter,
            )
            current_state.update(writing_res)

        if mode in ("full_pipeline", "review_only"):
            review_res = await call_review_graph_node(
                current_state,
                llm_provider=self.llm_provider,
                reporter=self.reporter,
            )
            current_state.update(review_res)

        return current_state
