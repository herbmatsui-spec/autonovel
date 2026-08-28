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
    revise_writing_node,
)
from src.backend.workflows.state import MasterGraphState

logger = logging.getLogger(__name__)


def should_revise_writing(state: MasterGraphState) -> str:
    """レビュー結果、予算、および NarrativeState ハブのシグナルに基づいてリバイスを実行するか判定"""
    budget = state.get("revision_budget", 1)
    needs_eps = list(state.get("needs_revision_eps", []))
    if not needs_eps:
        rev_results = state.get("review_results", {})
        needs_eps = [ep for ep, r in rev_results.items() if r.get("requires_revision", False)]

    # ステップ 18: hub シグナル（連続性違反・好感度低下）も revise 判定に使う
    hub = state.get("narrative")
    if hub is not None:
        # 連続性違反があるエピソードを追加
        for violation in getattr(hub, "continuity_violations", []):
            ep_v = violation.get("ep") or violation.get("episode_num")
            if ep_v is not None and int(ep_v) not in needs_eps:
                needs_eps.append(int(ep_v))

        # 好感度低下検知（前話より好感度が低下しているエピソードがあれば追加）
        episodes_dict = getattr(hub, "episodes", {})
        sorted_eps = sorted(episodes_dict.keys())
        for i in range(1, len(sorted_eps)):
            prev_ep = sorted_eps[i - 1]
            curr_ep = sorted_eps[i]
            prev_aff = episodes_dict[prev_ep].get("affinity", {})
            curr_aff = episodes_dict[curr_ep].get("affinity", {})
            for char_name, curr_val in curr_aff.items():
                if char_name in prev_aff and curr_val < prev_aff[char_name]:
                    if int(curr_ep) not in needs_eps:
                        needs_eps.append(int(curr_ep))

    state["needs_revision_eps"] = needs_eps

    if needs_eps and budget > 0:
        return "revise_phase"
    return END


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
    bound_revise = functools.partial(
        revise_writing_node,
        llm_provider=llm_provider,
        writing_agent=writing_agent,
        reporter=reporter,
    )

    # ノード追加
    graph.add_node("plot_phase", bound_plot)
    graph.add_node("writing_phase", bound_writing)
    graph.add_node("review_phase", bound_review)
    graph.add_node("revise_phase", bound_revise)

    # エッジ接続 (Plot -> Writing -> Review -> [要修正 & budget>0 ? Revise : END] -> END)
    graph.add_edge(START, "plot_phase")
    graph.add_edge("plot_phase", "writing_phase")
    graph.add_edge("writing_phase", "review_phase")
    graph.add_conditional_edges(
        "review_phase",
        should_revise_writing,
        {
            "revise_phase": "revise_phase",
            END: END,
        },
    )
    graph.add_edge("revise_phase", END)

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

            if should_revise_writing(current_state) == "revise_phase":
                revise_res = await revise_writing_node(
                    current_state,
                    llm_provider=self.llm_provider,
                    writing_agent=self.writing_agent,
                    reporter=self.reporter,
                )
                current_state.update(revise_res)

        return current_state
