"""
src/backend/workflows/nodes/master_nodes.py - マスターオーケストレーター（MasterGraph）のサブグラフ呼び出しノード群
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from src.backend.sse_manager import get_sse_manager
from src.backend.workflows.adapters import (
    feed_continuity,
    update_affinity,
    update_erotic,
    update_narrative,
    update_quality,
)
from src.backend.workflows.graphs.plot_graph import compile_plot_graph
from src.backend.workflows.graphs.review_graph import compile_review_graph
from src.backend.workflows.graphs.writing_graph import compile_writing_graph
from src.backend.workflows.narrative_state import NarrativeState
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

    branch_id = state.get("active_branch_id") or state.get("branch_id", 1)

    hub = state.get("narrative") or NarrativeState(
        book_id=state.get("book_id", 1),
        branch_id=branch_id,
    )

    plot_meta = dict(state.get("metadata", {}))
    plot_meta["narrative_hub"] = hub.to_dict()

    plot_input: PlotGraphState = {
        "book_id": state.get("book_id", 1),
        "branch_id": branch_id,
        "genre": state.get("metadata", {}).get("genre", "ファンタジー"),
        "theme": state.get("metadata", {}).get("theme", "冒険"),
        "target_episodes": state.get("target_end_ep", 10) - state.get("target_start_ep", 1) + 1,
        "max_iterations": 2,
        "metadata": plot_meta,
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
        "narrative": hub,
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
    branch_id = state.get("active_branch_id") or state.get("branch_id", 1)
    enable_hitl = state.get("enable_hitl", False)
    hitl_timeout = state.get("hitl_timeout", 300.0)

    logger.info(f"[MasterGraph] Executing Writing Subgraph for Episodes {start_ep}..{end_ep} (Branch {branch_id})...")

    sse = get_sse_manager()
    writing_app = compile_writing_graph(llm_provider=llm_provider, writing_agent=writing_agent)
    writing_results: Dict[int, WritingGraphState] = dict(state.get("writing_results", {}))

    bible_state: Dict[str, Any] = dict(state.get("bible_state", {}))
    hub = state.get("narrative") or NarrativeState(
        book_id=state.get("book_id", 1),
        branch_id=branch_id,
    )

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

        prev_tail = ""
        if ep > 1 and (ep - 1) in writing_results:
            prev_draft = writing_results[ep - 1].get("draft_content", "")
            prev_tail = prev_draft[-500:] if len(prev_draft) > 500 else prev_draft

        writing_input: WritingGraphState = {
            "book_id": state.get("book_id", 1),
            "branch_id": branch_id,
            "ep_num": ep,
            "passion": 0.8,
            "max_ac_iter": 2,
            "prev_episode_tail": prev_tail,
            "sys_inst": "あなたは商業ライトノベルのベストセラー作家です。",
            "fw_prompt": f"第{ep}話の本文を執筆してください。",
            "enable_hitl": enable_hitl,
            "hitl_timeout": hitl_timeout,
        }

        res = await writing_app.ainvoke(writing_input)
        writing_results[ep] = res

        text = res.get("draft_content", "")
        await update_quality(hub, ep, text)
        update_affinity(hub, ep, text)
        await update_narrative(hub, ep, text)
        update_erotic(hub, ep, text)
        feed_continuity(hub, {"ep": ep, "episode_num": ep, "text": text})

        # ステップ 31: ドメインイベントバスへ EPISODE_WRITTEN 発行と集約
        try:
            from src.prototype.aggregator import aggregate
            from src.shared.domain_event_bus import (
                DomainEvent,
                NarrativeEventType,
                get_domain_event_bus,
            )

            bus = get_domain_event_bus()
            ev = DomainEvent(
                type=NarrativeEventType.EPISODE_WRITTEN,
                payload={
                    "text": text,
                    "scene": {"ep": ep, "episode_num": ep, "text": text},
                    "tension": hub.tension_curve[-1] if hub.tension_curve else 0.5,
                },
                book_id=state.get("book_id", 1),
                ep=ep,
            )
            await aggregate(bus, hub, ev)
        except Exception as bus_err:
            logger.debug(f"[MasterGraph] DomainEventBus publish ignored: {bus_err}")

        # [設計原則 P3] 各話完了時に bible_state へ直列に状態を書き込み（連続性の維持）
        bible_state[f"ep_{ep}"] = {
            "ep_num": ep,
            "char_count": len(text),
            "status": res.get("status", "draft_generated"),
        }

    return {
        "writing_results": writing_results,
        "bible_state": bible_state,
        "narrative": hub,
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
    bible_state = state.get("bible_state", {})
    hub = state.get("narrative") or NarrativeState(
        book_id=state.get("book_id", 1),
        branch_id=state.get("branch_id", 1),
    )

    logger.info(f"[MasterGraph] Starting Review Phase with bible_state containing {len(bible_state)} entries...")
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
            "metadata": {"bible_state": bible_state, "narrative_hub": hub.to_dict()},
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

    review_summary = {
        "total_reviewed": len(review_results),
        "requires_revision_count": sum(1 for r in review_results.values() if r.get("requires_revision", False)),
        "needs_revision_eps": [ep for ep, r in review_results.items() if r.get("requires_revision", False)],
    }

    metrics = dict(state.get("quality_metrics", {}))
    scores = [r.get("commercial_score", 0.0) for r in review_results.values() if "commercial_score" in r]
    if scores:
        metrics["commercial_scores"] = {ep: r.get("commercial_score", 0.0) for ep, r in review_results.items()}
        metrics["avg_commercial_score"] = sum(scores) / len(scores)

    # ステップ 21: ハブのサマリーをメトリクスへ出力
    metrics["narrative"] = hub.to_dict()

    return {
        "review_results": review_results,
        "review_summary": review_summary,
        "needs_revision_eps": review_summary["needs_revision_eps"],
        "quality_metrics": metrics,
        "narrative": hub,
        "narrative_report": hub.to_dict(),
        "current_phase": "all_completed",
        "status": "completed",
        "overall_progress": 1.0,
    }


async def revise_writing_node(
    state: MasterGraphState,
    *,
    llm_provider: Any = None,
    writing_agent: Any = None,
    reporter: Any = None,
) -> Dict[str, Any]:
    """
    【Master Node: Revise Writing Subgraph Node】
    要修正と判定されたエピソードのみを対象に WritingGraph を再実行し、差分再評価を行う。
    """
    review_results = state.get("review_results", {})
    needs_revision_eps = state.get(
        "needs_revision_eps",
        [ep for ep, r in review_results.items() if r.get("requires_revision", False)],
    )

    if not needs_revision_eps:
        return {"current_phase": "revise_skipped"}

    logger.info(f"[MasterGraph] Revising Writing Subgraph for Episodes {needs_revision_eps}...")
    sse = get_sse_manager()
    writing_app = compile_writing_graph(llm_provider=llm_provider, writing_agent=writing_agent)
    writing_results: Dict[int, WritingGraphState] = dict(state.get("writing_results", {}))

    hub = state.get("narrative") or NarrativeState(
        book_id=state.get("book_id", 1),
        branch_id=state.get("branch_id", 1),
    )

    for ep in needs_revision_eps:
        rev_info = review_results.get(ep, {})
        instructions = rev_info.get("revision_instructions", [])
        formatted_instructions = [
            inst.get("description", str(inst)) if isinstance(inst, dict) else str(inst)
            for inst in instructions
        ]
        inst_str = "\n- ".join(formatted_instructions) if formatted_instructions else "品質基準を満たすよう推敲してください。"

        # ステップ 19: 連続性違反および未回収伏線の要約をプロンプトへ付与
        extra_prompts = []
        if hub.continuity_violations:
            violations_for_ep = [
                v for v in hub.continuity_violations
                if (v.get("ep") == ep or v.get("episode_num") == ep or ("ep" not in v and "episode_num" not in v))
            ]
            if violations_for_ep:
                v_msgs = [f"- {v.get('field', 'continuity')}: {v.get('msg', str(v))}" for v in violations_for_ep]
                extra_prompts.append("連続性違反指摘:\n" + "\n".join(v_msgs))
        if hub.foreshadow_registry:
            unresolved = [f for f in hub.foreshadow_registry if not f.get("resolved", False)]
            if unresolved:
                extra_prompts.append(f"未回収伏線: {len(unresolved)}件に留意してください。")

        extra_str = ("\n" + "\n".join(extra_prompts)) if extra_prompts else ""

        await sse.broadcast(
            "pipeline_progress",
            {
                "phase": "revising",
                "current_ep": ep,
                "progress": 0.85,
                "message": f"第{ep}話 指摘に基づき再執筆・推敲中...",
            },
        )

        if reporter and hasattr(reporter, "report"):
            await reporter.report(0.85, f"第{ep}話 指摘に基づき再執筆・推敲中...")

        prev_tail = ""
        if ep > 1 and (ep - 1) in writing_results:
            prev_draft = writing_results[ep - 1].get("draft_content", "")
            prev_tail = prev_draft[-500:] if len(prev_draft) > 500 else prev_draft

        writing_input: WritingGraphState = {
            "book_id": state.get("book_id", 1),
            "branch_id": state.get("branch_id", 1),
            "ep_num": ep,
            "passion": 0.8,
            "max_ac_iter": 2,
            "prev_episode_tail": prev_tail,
            "sys_inst": "あなたは商業ライトノベルのベストセラー作家です。",
            "fw_prompt": f"前回の推敲指摘:\n- {inst_str}{extra_str}\n第{ep}話の本文を再執筆してください。",
        }

        res = await writing_app.ainvoke(writing_input)
        writing_results[ep] = res

        # ステップ 19: 再執筆後に全アダプタで hub を再更新
        text = res.get("draft_content", "")
        await update_quality(hub, ep, text)
        update_affinity(hub, ep, text)
        await update_narrative(hub, ep, text)
        update_erotic(hub, ep, text)
        feed_continuity(hub, {"ep": ep, "episode_num": ep, "text": text})

    # 該当話のみ ReviewGraph を1回再実行し再集計
    review_app = compile_review_graph(llm_provider=llm_provider)
    updated_review_results: Dict[int, ReviewGraphState] = dict(review_results)

    for ep in needs_revision_eps:
        review_input: ReviewGraphState = {
            "book_id": state.get("book_id", 1),
            "branch_id": state.get("branch_id", 1),
            "ep_num": ep,
            "source_content": writing_results[ep].get("draft_content", ""),
            "metadata": {"bible_state": state.get("bible_state", {}), "narrative_hub": hub.to_dict()},
        }
        r_res = await review_app.ainvoke(review_input)
        updated_review_results[ep] = r_res

    new_needs_eps = [
        ep for ep, r in updated_review_results.items() if r.get("requires_revision", False)
    ]
    is_converged = len(new_needs_eps) < len(needs_revision_eps)

    new_review_summary = {
        "total_reviewed": len(updated_review_results),
        "requires_revision_count": len(new_needs_eps),
        "needs_revision_eps": new_needs_eps,
        "is_converged": is_converged,
    }

    # 予算消費と収束判定（減らなければ残予算を0にリセットして終了）
    current_budget = state.get("revision_budget", 1)
    new_budget = max(0, current_budget - 1) if is_converged else 0

    metrics = dict(state.get("quality_metrics", {}))
    metrics["revision_converged"] = is_converged
    metrics["initial_revision_needed_eps"] = needs_revision_eps
    metrics["remaining_revision_needed_eps"] = new_needs_eps
    metrics["narrative"] = hub.to_dict()

    return {
        "writing_results": writing_results,
        "review_results": updated_review_results,
        "review_summary": new_review_summary,
        "needs_revision_eps": new_needs_eps,
        "revision_budget": new_budget,
        "quality_metrics": metrics,
        "narrative": hub,
        "narrative_report": hub.to_dict(),
        "current_phase": "revise_completed",
    }
