"""plot_rebuild_workflow.py - プロット再構築パイプライン (Proposal C)。

責務の分割:
    PlanningAgent (= self.planner) : アーク生成のみ (generate_arcs)
    PlotExpander   (= self.plot_agent): プロット展開のみ (expand_plots)

PlotRebuildWorkflow は両者を組み合わせて、以下の 5 ステップの
パイプラインとして再構築を orchestration する:

    1. 新規アーク生成      -> PlanningAgent.generate_arcs
    2. アーク監査          -> PlanAuditor.audit_bible_completeness (任意)
    3. 影響エピソード展開  -> PlotExpander.expand_plots
    4. 整合性監査          -> LogicalAuditor.audit_plot_as_issues (任意)
    5. 結果統合            -> ArcBlueprint + PlotDetail を dict に統合

いずれかのステップが失敗してもパイプラインは停止せず、可能な範囲で
部分結果を返す（graceful degradation）。

Returns (execute):
    {
        "done": bool,
        "arcs": List[dict],            # 生成されたアーク (ArcBlueprint)
        "expanded": List[dict],        # 展開されたプロット (PlotDetail)
        "count": int,                  # expanded の件数
        "metadata": {                  # パイプライン実行時の文脈
            "book_id", "book_title", "start_ep", "new_total", "branch_id"
        },
        "error": str (失敗時のみ),
    }

パイプライン図::

    PlanningAgent --(generate_arcs)--> [Step1] --> [Step2 audit]
                                                --> PlotExpander --(expand_plots)--> [Step3]
                                                --> [Step4 audit] --> [Step5 assemble]
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, cast

from src.core.interfaces import IReporter
from src.models.plot import ArcBlueprint, ArcList
from src.shared.utils import StatusReporter

from .base_workflow import BaseWorkflow

logger = logging.getLogger(__name__)


class _NullReporter(IReporter):
    """reporter が渡されなかった場合の no-op 実装 (IReporter 互換)."""

    def report(self, msg: str, level: str = "info") -> None:  # noqa: ANN401, D401
        pass

    def update_progress(self, current: int, total: int, status: str = "") -> None:  # noqa: ANN401
        pass


class PlotRebuildWorkflow(BaseWorkflow):
    """プロット再構築パイプライン: アーク生成から詳細展開までを実行する。

    PlanningAgent にはアーク生成を、PlotExpander にはプロット展開を委譲し、
    再構築に伴う監査・統合をこのワークフローが orchestration する。
    """

    async def execute(self, reporter: Optional[StatusReporter], **kwargs: Any) -> Dict[str, Any]:
        params = kwargs.get("params", {})
        active_reporter: Any = reporter or _NullReporter()
        try:
            active_reporter.report("🔧 プロット再構築パイプラインを開始します...", "info")

            context = await self._build_rebuild_context(params, active_reporter)
            active_reporter.report(
                f"📋 再構築対象: 第{context['start_ep']}話〜第{context['new_total']}話", "info"
            )
            new_arcs = await self._step1_generate_new_arcs(context, params, active_reporter)
            self._step2_audit_arcs(new_arcs, active_reporter)
            expanded = await self._step3_expand_affected_eps(
                context, new_arcs, params, active_reporter
            )
            self._step4_audit_expanded(new_arcs, expanded, context, params, active_reporter)
            active_reporter.report("🎉 プロット再構築パイプライン完了", "success")
            return self._step5_assemble_result(new_arcs, expanded, context, params)
        except Exception as e:  # noqa: BLE001
            logger.error("プロット再構築パイプライン失敗: %s", e)
            active_reporter.report(f"🚨 プロット再構築に失敗しました: {e}", "error")
            return {"done": False, "error": str(e), "arcs": [], "expanded": [], "count": 0}

    # ------------------------------------------------------------------
    # コンテキスト構築
    # ------------------------------------------------------------------
    async def _build_rebuild_context(
        self, params: Dict[str, Any], reporter: IReporter
    ) -> Dict[str, Any]:
        """作品情報・Bible・過去プロットを聚合したコンテキストを構築する."""
        book_id = int(params["book_id"])
        start_ep = int(params["start_ep"])
        new_total = int(params["new_total"])

        book = None
        branch_id = 1
        book_title = ""
        if self.repo is not None:
            try:
                book = await self.repo.get_book(book_id)
                if book is not None:
                    book_title = getattr(book, "title", "") or ""
                    branch_id = getattr(book, "current_branch_id", None) or 1
            except Exception as e:  # noqa: BLE001
                logger.warning("作品情報取得スキップ: %s", e)

        return {
            "book_id": book_id,
            "start_ep": start_ep,
            "new_total": new_total,
            "branch_id": branch_id,
            "book_title": book_title,
        }

    # ------------------------------------------------------------------
    # ステップ1: 新規アーク生成
    # ------------------------------------------------------------------
    async def _step1_generate_new_arcs(
        self, context: Dict[str, Any], params: Dict[str, Any], reporter: IReporter
    ) -> ArcList:
        try:
            reporter.report(f"📐 第{context['start_ep']}話以降の新規アークを生成中...", "info")
            synopsis = (
                f"{params.get('trend_memo', '')}\nキーワード: {params.get('new_keywords', '')}"
            )
            planner = cast(Any, self.planner)
            result = await planner.generate_arcs(
                title=context["book_title"],
                synopsis=synopsis,
                target_eps=context["new_total"],
                start_ep=context["start_ep"],
            )
            new_arcs = result if isinstance(result, ArcList) else ArcList.model_validate(result)
            reporter.report(f"✅ アーク生成完了: {len(new_arcs.arcs)} 件", "success")
            return new_arcs
        except Exception as e:  # noqa: BLE001
            logger.error("ステップ1 アーク生成失敗: %s", e)
            reporter.report(f"⚠️ アーク生成に失敗しました: {e}", "warning")
            raise

    # ------------------------------------------------------------------
    # ステップ2: アーク監査 (任意)
    # ------------------------------------------------------------------
    def _step2_audit_arcs(self, new_arcs: ArcList, reporter: IReporter) -> None:
        plan_auditor = getattr(self.planner, "plan_auditor", None)
        if plan_auditor is None or not hasattr(plan_auditor, "audit_bible_completeness"):
            reporter.report("ℹ️ アーク監査をスキップ (PlanAuditor 未設定)", "info")
            return
        try:
            bible_like = {"arcs": [a.model_dump() for a in new_arcs.arcs]}
            is_consistent = plan_auditor.audit_bible_completeness(bible_like, reporter=reporter)
            if not is_consistent:
                issues: List[str] = []
                reporter.report("⚠️ ステップ2監査課題: " + "; ".join(issues), "warning")
        except Exception as e:  # noqa: BLE001
            logger.warning("ステップ2 監査スキップ: %s", e)

    # ------------------------------------------------------------------
    # ステップ3: 影響エピソード展開
    # ------------------------------------------------------------------
    async def _step3_expand_affected_eps(
        self,
        context: Dict[str, Any],
        new_arcs: ArcList,
        params: Dict[str, Any],
        reporter: IReporter,
    ) -> List[Any]:
        ep_nums = list(range(context["start_ep"], context["new_total"] + 1))
        arcs: List[ArcBlueprint] = new_arcs.arcs
        plot_agent = cast(Any, self.plot_agent)
        try:
            reporter.report(
                f"✍️ 第{context['start_ep']}話〜第{context['new_total']}話を展開中...", "info"
            )
            expanded = await plot_agent.expand_plots(
                book_id=context["book_id"],
                target_ep_list=ep_nums,
                arcs=arcs,
                reporter=reporter,
                force=True,
                branch_id=context["branch_id"],
            )
            result: List[Any] = list(expanded) if expanded else []
            reporter.report(f"✅ プロット展開完了: {len(result)} 話", "success")
            return result
        except Exception as e:  # noqa: BLE001
            logger.error("ステップ3 展開失敗: %s", e)
            reporter.report(f"⚠️ プロット展開に失敗しました: {e}", "warning")
            return []

    # ------------------------------------------------------------------
    # ステップ4: 整合性監査 (任意)
    # ------------------------------------------------------------------
    def _step4_audit_expanded(
        self,
        new_arcs: ArcList,
        expanded: List[Any],
        context: Dict[str, Any],
        params: Dict[str, Any],
        reporter: IReporter,
    ) -> None:
        auditor = getattr(self, "auditor", None)
        if auditor is None or not hasattr(auditor, "audit_plot_as_issues"):
            return
        try:
            for arc in new_arcs.arcs:
                issues = auditor.audit_plot_as_issues(
                    book_id=context["book_id"],
                    branch_id=context["branch_id"],
                    ep_num=arc.end_ep,
                    summary=arc.summary,
                )
                if hasattr(issues, "is_consistent") and not issues.is_consistent:
                    reporter.report(f"⚠️ 第{arc.arc_num}アーク監査課題: {issues}", "warning")
        except Exception as e:  # noqa: BLE001
            logger.warning("ステップ4 監査スキップ: %s", e)

    # ------------------------------------------------------------------
    # ステップ5: 結果統合
    # ------------------------------------------------------------------
    def _step5_assemble_result(
        self,
        new_arcs: ArcList,
        expanded: Optional[List[Any]],
        context: Dict[str, Any],
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        expanded_list = expanded or []
        return {
            "done": True,
            "arcs": [a.model_dump() for a in new_arcs.arcs],
            "expanded": [_dump(p) for p in expanded_list],
            "count": len(expanded_list),
            "metadata": {
                "book_id": context["book_id"],
                "book_title": context["book_title"],
                "start_ep": context["start_ep"],
                "new_total": context["new_total"],
                "branch_id": context["branch_id"],
            },
        }


def _dump(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "model_dump"):
        return cast(Dict[str, Any], obj.model_dump())
    if isinstance(obj, dict):
        return obj
    return {"value": str(obj)}
