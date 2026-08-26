"""
src/backend/workflows/graphs/writing_graph.py - 執筆・自己推敲マルチエージェントグラフ (WritingGraph)
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

from src.backend.workflows.edges.writing_edges import check_audit_results
from src.backend.workflows.nodes.writing_nodes import (
    build_context_node,
    generate_draft_node,
    self_audit_node,
)
from src.backend.workflows.state import WritingGraphState

logger = logging.getLogger(__name__)


def create_writing_graph(llm_provider: Any = None, writing_agent: Any = None) -> Any:
    """WritingGraph の StateGraph を定義して構築する"""
    if not HAS_LANGGRAPH or StateGraph is None:
        logger.warning("[WritingGraph] LangGraph is not available. Falling back to sequential execution wrapper.")
        return SequentialWritingGraphFallback(llm_provider=llm_provider, writing_agent=writing_agent)

    graph = StateGraph(WritingGraphState)

    # 依存性注入
    bound_ctx_node = functools.partial(build_context_node, writing_agent=writing_agent)
    bound_draft_node = functools.partial(generate_draft_node, llm_provider=llm_provider)
    bound_audit_node = functools.partial(self_audit_node, llm_provider=llm_provider)

    # ノード追加
    graph.add_node("build_context", bound_ctx_node)
    graph.add_node("generate_draft", bound_draft_node)
    graph.add_node("self_audit", bound_audit_node)

    # エッジ接続
    graph.add_edge(START, "build_context")
    graph.add_edge("build_context", "generate_draft")
    graph.add_edge("generate_draft", "self_audit")

    # 条件付きエッジ (監査合否 -> 終了 or 再生成)
    graph.add_conditional_edges(
        "self_audit",
        check_audit_results,
        {
            "generate_draft": "generate_draft",
            "__end__": END,
        },
    )

    return graph


def compile_writing_graph(llm_provider: Any = None, writing_agent: Any = None, checkpointer: Any = None) -> Any:
    """WritingGraph をコンパイルして実行可能オブジェクトを返す"""
    builder = create_writing_graph(llm_provider=llm_provider, writing_agent=writing_agent)
    if hasattr(builder, "compile"):
        return builder.compile(checkpointer=checkpointer)
    return builder


class SequentialWritingGraphFallback:
    """LangGraph 非導入環境用のフォールバックシーケンシャル実行クラス"""

    def __init__(self, llm_provider: Any = None, writing_agent: Any = None):
        self.llm_provider = llm_provider
        self.writing_agent = writing_agent

    async def ainvoke(self, state: WritingGraphState) -> WritingGraphState:
        """非同期でノードを実行してActor-Criticループをエミュレート"""
        current_state = dict(state)
        ctx_res = await build_context_node(current_state, writing_agent=self.writing_agent)
        current_state.update(ctx_res)

        max_iter = current_state.get("max_ac_iter", 3)
        for _ in range(max_iter):
            draft_res = await generate_draft_node(current_state, llm_provider=self.llm_provider)
            current_state.update(draft_res)

            audit_res = await self_audit_node(current_state, llm_provider=self.llm_provider)
            current_state.update(audit_res)

            decision = check_audit_results(current_state)
            if decision == "__end__":
                break

        return current_state
