"""
src/backend/workflows/nodes/master_nodes.py - マスターオーケストレーター（MasterGraph）のサブグラフ呼び出しノード群
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from src.backend.sse_manager import get_sse_manager
from src.backend.workflows.graphs.plot_graph import compile_plot_graph
from src.backend.workflows.graphs.review_graph import compile_review_graph
from src.backend.workflows.graphs.writing_graph import compile_writing_graph
from src.backend.workflows.state import (
    MasterGraphState,
    PlotGraphState,
    ReviewGraphState,
    WritingGraphState,
)

logger = logging.getLogger(__name__)


async def call_plot_graph_node(
    state: MasterGraphState,
    *,
    llm_provider: Any = None,
    reporter: Any = None,
) -> Dict[str, Any]:
    """
    【Master Node 1: Plot Pipeline Execution】
    PlotGraph サブグラフを実行し、プロットを生成・推敲する。
    """
    logger.info(f"[MasterGraph] Executing Plot Subgraph for task {state.get('task_id')}...")
    
    sse = get_sse_manager()
    await sse.broadcast(
        "pipeline_progress",
        {
            "phase": "plot",
            "progress": 0.20,
            "message": "プロット生成・推敲グラフを実行中...",
        },
    )

    if reporter and hasattr(reporter, "report"):
        await reporter.report(0.2, "プロット生成・推敲グラフを実行中...")

    plot_app = compile_plot_graph(llm_provider=llm_provider)

    plot_input: PlotGraphState = {
        "book_id": state.get("book_id", 1),
        "branch_id": state.get("branch_id", 1),
        "genre": state.get("metadata", {}).get("genre", "ファンタジー"),
        "theme": state.get("metadata", {}).get("theme", "冒険"),
        "target_episodes": state.get("target_end_ep", 10) - state.get("target_start_ep", 1) + 1,
        "max_iterations": 2,
    }

    plot_result = await plot_app.ainvoke(plot_input)

    await sse.broadcast(
        "pipeline_progress",
        {
            "phase": "plot_completed",
            "progress": 0.35,
            "message": "プロット策定・推敲フェーズが完了しました。",
        },
    )

    return {
        "plot_result": plot_result,
        "current_phase": "plot_completed",
        "overall_progress": 0.35,
    }


async def call_writing_graph_node(
    state: MasterGraphState,
    *,
    llm_provider: Any = None,
    writing_agent: Any = None,
    reporter: Any = None,
) -> Dict[str, Any]:
    """
    【Master Node 2: Writing Pipeline Execution】
    WritingGraph サブグラフを各対象エピソードに対して実行する。
    """
    start_ep = state.get("target_start_ep", 1)
    end_ep = state.get("target_end_ep", 1)
    logger.info(f"[MasterGraph] Executing Writing Subgraph for Episodes {start_ep}..{end_ep}...")

    sse = get_sse_manager()
    writing_app = compile_writing_graph(llm_provider=llm_provider, writing_agent=writing_agent)
    writing_results: Dict[int, WritingGraphState] = dict(state.get("writing_results", {}))

    for ep in range(start_ep, end_ep + 1):
        progress = 0.35 + (0.45 * ((ep - start_ep + 1) / max(1, (end_ep - start_ep + 1))))
        
        await sse.broadcast(
            "pipeline_progress",
            {
                "phase": "writing",
                "current_ep": ep,
                "progress": round(progress, 2),
                "message": f"第{ep}話 執筆・自己推敲グラフを実行中...",
            },
        )

        if reporter and hasattr(reporter, "report"):
            await reporter.report(progress, f"第{ep}話 執筆・自己推敲グラフを実行中...")

        writing_input: WritingGraphState = {
            "book_id": state.get("book_id", 1),
            "branch_id": state.get("branch_id", 1),
            "ep_num": ep,
            "passion": 0.8,
            "max_ac_iter": 2,
            "sys_inst": "あなたは商業ライトノベルのベストセラー作家です。",
            "fw_prompt": f"第{ep}話の本文を執筆してください。",
        }

        res = await writing_app.ainvoke(writing_input)
        writing_results[ep] = res

    return {
        "writing_results": writing_results,
        "current_phase": "writing_completed",
        "overall_progress": 0.80,
    }


async def call_review_graph_node(
    state: MasterGraphState,
    *,
    llm_provider: Any = None,
    reporter: Any = None,
) -> Dict[str, Any]:
    """
    【Master Node 3: Review & Final Audit Pipeline Execution】
    ReviewGraph サブグラフを実行し、生成された全エピソードの最終監査を行う。
    """
    writing_results = state.get("writing_results", {})
    review_app = compile_review_graph(llm_provider=llm_provider)
    review_results: Dict[int, ReviewGraphState] = dict(state.get("review_results", {}))

    sse = get_sse_manager()

    for ep_num, w_res in writing_results.items():
        await sse.broadcast(
            "pipeline_progress",
            {
                "phase": "review",
                "current_ep": ep_num,
                "progress": 0.90,
                "message": f"第{ep_num}話 最終品質監査グラフを実行中...",
            },
        )

        if reporter and hasattr(reporter, "report"):
            await reporter.report(0.90, f"第{ep_num}話 最終品質監査グラフを実行中...")

        review_input: ReviewGraphState = {
            "book_id": state.get("book_id", 1),
            "branch_id": state.get("branch_id", 1),
            "ep_num": ep_num,
            "source_content": w_res.get("draft_content", ""),
        }

        res = await review_app.ainvoke(review_input)
        review_results[ep_num] = res

    await sse.broadcast(
        "pipeline_progress",
        {
            "phase": "completed",
            "progress": 1.0,
            "message": "全パイプライン実行完了。最高品質の原稿が出力されました！",
        },
    )

    if reporter and hasattr(reporter, "report"):
        await reporter.report(1.0, "全パイプライン実行完了")

    return {
        "review_results": review_results,
        "current_phase": "all_completed",
        "status": "completed",
        "overall_progress": 1.0,
    }
