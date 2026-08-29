"""
src/backend/workflows/graphs/writing_graph.py - 執筆・自己推敲マルチエージェントグラフ (WritingGraph)
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

from src.backend.workflows.edges.writing_edges import check_audit_results
from src.backend.workflows.nodes.writing_nodes import (
    auto_illustration_node,
    build_context_node,
    generate_draft_node,
    hitl_review_node,
    self_audit_node,
)
from src.backend.workflows.state import WritingGraphState

logger = logging.getLogger(__name__)


def create_writing_graph(
    llm_provider: Any = None,
    writing_agent: Any = None,
    illustration_agent: Any = None,
    hitl_manager: Any = None,
) -> Any:
    """WritingGraph の StateGraph を定義して構築する"""
    if not HAS_LANGGRAPH or StateGraph is None:
        logger.warning("[WritingGraph] LangGraph is not available. Falling back to sequential execution wrapper.")
        return SequentialWritingGraphFallback(
            llm_provider=llm_provider,
            writing_agent=writing_agent,
            illustration_agent=illustration_agent,
            hitl_manager=hitl_manager,
        )

    graph = StateGraph(WritingGraphState)

    # 依存性注入
    bound_ctx_node = functools.partial(build_context_node, writing_agent=writing_agent)
    bound_draft_node = functools.partial(generate_draft_node, llm_provider=llm_provider)
    bound_hitl_node = functools.partial(hitl_review_node, hitl_manager=hitl_manager)
    bound_audit_node = functools.partial(self_audit_node, llm_provider=llm_provider)
    bound_illo_node = functools.partial(auto_illustration_node, illustration_agent=illustration_agent)

    # ノード追加
    graph.add_node("build_context", bound_ctx_node)
    graph.add_node("generate_draft", bound_draft_node)
    graph.add_node("hitl_review", bound_hitl_node)
    graph.add_node("self_audit", bound_audit_node)
    graph.add_node("auto_illustration", bound_illo_node)

    # エッジ接続
    graph.add_edge(START, "build_context")
    graph.add_edge("build_context", "generate_draft")
    graph.add_edge("generate_draft", "hitl_review")
    graph.add_edge("hitl_review", "self_audit")
    graph.add_edge("auto_illustration", END)

    # 条件付きエッジ (監査合否 -> 終了 or 再生成 or 自動イラスト)
    graph.add_conditional_edges(
        "self_audit",
        check_audit_results,
        {
            "generate_draft": "generate_draft",
            "auto_illustration": "auto_illustration",
            "__end__": END,
        },
    )

    return graph


def compile_writing_graph(
    llm_provider: Any = None,
    writing_agent: Any = None,
    illustration_agent: Any = None,
    hitl_manager: Any = None,
    checkpointer: Any = None,
) -> Any:
    """WritingGraph をコンパイルして実行可能オブジェクトを返す"""
    builder = create_writing_graph(
        llm_provider=llm_provider,
        writing_agent=writing_agent,
        illustration_agent=illustration_agent,
        hitl_manager=hitl_manager,
    )
    if hasattr(builder, "compile"):
        return builder.compile(checkpointer=checkpointer)
    return builder


class SequentialWritingGraphFallback:
    """LangGraph 非導入環境用のフォールバックシーケンシャル実行クラス"""

    def __init__(
        self,
        llm_provider: Any = None,
        writing_agent: Any = None,
        illustration_agent: Any = None,
        hitl_manager: Any = None,
    ):
        self.llm_provider = llm_provider
        self.writing_agent = writing_agent
        self.illustration_agent = illustration_agent
        self.hitl_manager = hitl_manager

    async def ainvoke(self, state: WritingGraphState) -> WritingGraphState:
        """非同期でノードを実行してActor-Criticループをエミュレート"""
        current_state = dict(state)
        ctx_res = await build_context_node(current_state, writing_agent=self.writing_agent)
        current_state.update(ctx_res)

        max_iter = current_state.get("max_ac_iter", 3)
        for _ in range(max_iter):
            draft_res = await generate_draft_node(current_state, llm_provider=self.llm_provider)
            current_state.update(draft_res)

            hitl_res = await hitl_review_node(current_state, hitl_manager=self.hitl_manager)
            current_state.update(hitl_res)

            audit_res = await self_audit_node(current_state, llm_provider=self.llm_provider)
            current_state.update(audit_res)

            decision = check_audit_results(current_state)
            if decision == "auto_illustration":
                illo_res = await auto_illustration_node(
                    current_state,
                    illustration_agent=self.illustration_agent,
                )
                current_state.update(illo_res)
                break
            elif decision == "__end__":
                break

        return current_state
