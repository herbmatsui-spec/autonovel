"""
src/backend/workflows/graphs/plot_graph.py - プロット生成・自己改善マルチエージェントグラフ (PlotGraph)
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

from src.backend.workflows.edges.plot_edges import should_refine_plot
from src.backend.workflows.nodes.plot_nodes import (
    evaluate_plot_node,
    generate_initial_plot_node,
    refine_plot_node,
)
from src.backend.workflows.state import PlotGraphState

logger = logging.getLogger(__name__)


def create_plot_graph(llm_provider: Any = None) -> Any:
    """PlotGraph の StateGraph を定義して構築する"""
    if not HAS_LANGGRAPH or StateGraph is None:
        logger.warning("[PlotGraph] LangGraph is not available. Falling back to sequential execution wrapper.")
        return SequentialPlotGraphFallback(llm_provider=llm_provider)

    graph = StateGraph(PlotGraphState)

    # 依存性注入（llm_provider を各ノードに束縛）
    bound_init_node = functools.partial(generate_initial_plot_node, llm_provider=llm_provider)
    bound_eval_node = functools.partial(evaluate_plot_node, llm_provider=llm_provider)
    bound_refine_node = functools.partial(refine_plot_node, llm_provider=llm_provider)

    # ノード追加
    graph.add_node("generate_initial_plot", bound_init_node)
    graph.add_node("evaluate_plot", bound_eval_node)
    graph.add_node("refine_plot", bound_refine_node)

    # エッジ接続
    graph.add_edge(START, "generate_initial_plot")
    graph.add_edge("generate_initial_plot", "evaluate_plot")

    # 条件付きエッジ (評価 -> 改善 or 終了)
    graph.add_conditional_edges(
        "evaluate_plot",
        should_refine_plot,
        {
            "refine_plot": "refine_plot",
            "__end__": END,
        },
    )

    # 改善 -> 再評価 (ループ形成)
    graph.add_edge("refine_plot", "evaluate_plot")

    return graph


def compile_plot_graph(llm_provider: Any = None, checkpointer: Any = None) -> Any:
    """PlotGraph をコンパイルして実行可能オブジェクトを返す"""
    builder = create_plot_graph(llm_provider=llm_provider)
    if hasattr(builder, "compile"):
        return builder.compile(checkpointer=checkpointer)
    return builder


class SequentialPlotGraphFallback:
    """LangGraph 非導入環境用のフォールバックシーケンシャル実行クラス"""

    def __init__(self, llm_provider: Any = None):
        self.llm_provider = llm_provider

    async def ainvoke(self, state: PlotGraphState) -> PlotGraphState:
        """非同期でノードを実行して自己修正ループをエミュレート"""
        current_state = dict(state)
        init_res = await generate_initial_plot_node(current_state, llm_provider=self.llm_provider)
        current_state.update(init_res)

        max_iter = current_state.get("max_iterations", 3)
        for _ in range(max_iter):
            eval_res = await evaluate_plot_node(current_state, llm_provider=self.llm_provider)
            current_state.update(eval_res)

            decision = should_refine_plot(current_state)
            if decision == "__end__":
                break

            refine_res = await refine_plot_node(current_state, llm_provider=self.llm_provider)
            current_state.update(refine_res)

        return current_state
