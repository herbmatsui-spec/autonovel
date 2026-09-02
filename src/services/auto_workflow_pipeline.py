from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from src.models import FullAutoWorkflowResult
from src.services.pipeline_base import WorkflowContext, WorkflowStep

# 新規 Step 実装をインポート
from src.services.pipeline_steps import (
    AuditRewriteStep,
    CatharsisAnalysisStep,
    IllustrationStep,
    MarketingStep,
    PackageStep,
    PlanStep,
    WriteStep,
)

if TYPE_CHECKING:
    from src.backend.background import StatusReporter
    from src.backend.engine import UltimateHegemonyEngine

logger = logging.getLogger(__name__)


# InferenceStep は既存のまま維持 (高機能のため)
class InferenceStep(WorkflowStep):
    async def execute(
        self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter
    ) -> bool:
        if ctx.user_prompt:
            try:
                reporter.report(
                    f"🔮 1行プロンプトから覇権企画を自動強化（推論）中: 「{ctx.user_prompt}」",
                    "info",
                )
                inference = await engine.planner.infer_easy_mode_params(
                    ctx.user_prompt, reporter=reporter
                )

                ctx.genre = inference.genre_key or ctx.genre
                ctx.concept = (
                    f"{ctx.concept}\n{inference.core_idea}".strip()
                    if ctx.concept
                    else inference.core_idea
                )
                if inference.mc_concept:
                    ctx.keywords = (
                        f"{ctx.keywords}, {inference.mc_concept}"
                        if ctx.keywords
                        else inference.mc_concept
                    )
                ctx.title = inference.title_idea
                reporter.report(
                    f"✨ 自動強化完了！ ジャンル: {ctx.genre} / コンセプト推論成功", "info"
                )
            except Exception as e:
                reporter.report(
                    f"⚠️ 自動強化に失敗しましたが、既存のパラメータで続行します。: {e}", "warning"
                )
        return True


class AutoWorkflowPipeline:
    def __init__(self, steps: list[WorkflowStep]):
        self.steps = steps

    async def execute(
        self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter
    ) -> FullAutoWorkflowResult:
        reporter.report("🚀 全自動モード開始！", "info")

        for step in self.steps:
            success = await step.execute(ctx, engine, reporter)
            if not success:
                status = "stopped" if reporter.state.should_stop() else "failed"
                if isinstance(step, PlanStep) and not reporter.state.should_stop():
                    status = "failed_integrity_check"
                return FullAutoWorkflowResult(
                    book_id=ctx.book_id,
                    title=ctx.title,
                    chars_count=ctx.chars_count,
                    failed_episodes=ctx.failed_episodes,
                    status=status,
                    easy_parameters=ctx.easy_parameters,
                    average_audit_score=ctx.average_audit_score,
                    episodes_detail=ctx.episodes_detail,
                    spice_guard_enabled=ctx.enable_spice_guard,
                    illustrations=getattr(ctx, "illustrations", []),
                    marketing_pack=getattr(ctx, "marketing_pack", None),
                )

        return FullAutoWorkflowResult(
            book_id=ctx.book_id,
            title=ctx.title,
            chars_count=ctx.chars_count,
            failed_episodes=ctx.failed_episodes,
            zip_data=ctx.zip_data,
            zip_filename=ctx.zip_filename,
            status="success",
            easy_parameters=ctx.easy_parameters,
            average_audit_score=ctx.average_audit_score,
            episodes_detail=ctx.episodes_detail,
            spice_guard_enabled=ctx.enable_spice_guard,
            illustrations=getattr(ctx, "illustrations", []),
            marketing_pack=getattr(ctx, "marketing_pack", None),
        )


# ============================================================================
# パイプライン構築関数 (Step 18-19)
# ============================================================================

def create_full_auto_pipeline(
    enable_spice_guard: bool = False,
    enable_illustration: bool = False,
    enable_catharsis_analysis: bool = True,
    enable_marketing: bool = True,
    max_retries: int = 1,
) -> AutoWorkflowPipeline:
    """
    全自動モード用パイプライン構築
    - FullAutoWorkflow 相当の機能
    - SpiceGuard はデフォルト無効 (FullAuto 互換)
    """
    steps = [
        InferenceStep(),
        PlanStep(),
        CatharsisAnalysisStep() if enable_catharsis_analysis else None,
        WriteStep(),
        AuditRewriteStep() if enable_spice_guard else None,
        IllustrationStep() if enable_illustration else None,
        MarketingStep() if enable_marketing else None,
        PackageStep(),
    ]
    # None を除外
    steps = [s for s in steps if s is not None]
    return AutoWorkflowPipeline(steps)


def create_easy_mode_pipeline(
    genre: str = "ファンタジー",
    target_episodes: int = 8,
    enable_spice_guard: bool = True,
    max_rewrite_iterations: int = 3,
    target_audit_score: float = 95.0,
    enable_marketing: bool = True,
) -> AutoWorkflowPipeline:
    """
    かんたんモード用パイプライン構築
    - EasyModePipeline 相当の機能
    - SpiceGuard デフォルト有効
    - カタルシス分析は無効 (EasyMode では未実装)
    - 挿絵生成は無効
    """
    steps = [
        InferenceStep(),
        PlanStep(),
        WriteStep(),
        AuditRewriteStep() if enable_spice_guard else None,
        MarketingStep() if enable_marketing else None,
        PackageStep(),
    ]
    steps = [s for s in steps if s is not None]
    pipeline = AutoWorkflowPipeline(steps)
    # パイプライン固有のデフォルト設定は呼び出し側で Context に設定
    return pipeline


def create_custom_pipeline(
    steps: list[WorkflowStep] | None = None,
    **step_options,
) -> AutoWorkflowPipeline:
    """
    カスタムパイプライン構築 (テスト・実験用)
    """
    if steps is not None:
        return AutoWorkflowPipeline(steps)

    # オプションベースで動的構築
    step_list = []
    if step_options.get("inference", True):
        step_list.append(InferenceStep())
    if step_options.get("plan", True):
        step_list.append(PlanStep())
    if step_options.get("catharsis", False):
        step_list.append(CatharsisAnalysisStep())
    if step_options.get("write", True):
        step_list.append(WriteStep())
    if step_options.get("audit_rewrite", False):
        step_list.append(AuditRewriteStep())
    if step_options.get("illustration", False):
        step_list.append(IllustrationStep())
    if step_options.get("marketing", True):
        step_list.append(MarketingStep())
    step_list.append(PackageStep())

    return AutoWorkflowPipeline(step_list)