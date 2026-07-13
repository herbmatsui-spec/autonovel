from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import BaseModel, Field

from src.models import FullAutoWorkflowResult

if TYPE_CHECKING:
    from src.backend.background import StatusReporter
    from src.backend.engine import UltimateHegemonyEngine

logger = logging.getLogger(__name__)

class WorkflowContext(BaseModel):
    genre: str
    keywords: str
    archetype_key: str
    target_eps: int
    initial_limit: int
    word_count: int
    concept: str = ""
    tone_vibe: float = 0.6
    user_prompt: str = ""
    book_id: Optional[int] = None
    chars_count: int = 0
    failed_episodes: List[Dict[str, Any]] = Field(default_factory=list)
    zip_data: Optional[bytes] = None
    zip_filename: Optional[str] = None
    title: str = ""
    easy_parameters: Dict[str, Any] = Field(default_factory=dict)

class WorkflowStep:
    async def execute(self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter) -> bool:
        """Execute step. Returns True to continue, False to halt/break."""
        raise NotImplementedError()

class InferenceStep(WorkflowStep):
    async def execute(self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter) -> bool:
        if ctx.user_prompt:
            try:
                reporter.report(f"🔮 1行プロンプトから覇権企画を自動強化（推論）中: 「{ctx.user_prompt}」", "info")
                inference = await engine.planner.infer_easy_mode_params(ctx.user_prompt, reporter=reporter)

                ctx.genre = inference.genre_key or ctx.genre
                ctx.concept = f"{ctx.concept}\n{inference.core_idea}".strip() if ctx.concept else inference.core_idea
                if inference.mc_concept:
                    ctx.keywords = f"{ctx.keywords}, {inference.mc_concept}" if ctx.keywords else inference.mc_concept
                ctx.title = inference.title_idea
                reporter.report(f"✨ 自動強化完了！ ジャンル: {ctx.genre} / コンセプト推論成功", "info")
            except Exception as e:
                reporter.report(f"⚠️ 自動強化に失敗しましたが、既存のパラメータで続行します。: {e}", "warning")
        return True

class PlanStep(WorkflowStep):
    async def execute(self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter) -> bool:
        from config import STORY_ARCHETYPES
        p_settings = STORY_ARCHETYPES.get(ctx.archetype_key, STORY_ARCHETYPES["王道ざまぁ（爽快感最大）"])
        try:
            reporter.update_progress(0, 3, "STEP 1/3: 覇権企画を生成中...")
            book_id, bible = await engine.planner.create_hegemony_plan(
                genre=ctx.genre,
                keywords=ctx.keywords,
                style_key=p_settings.get("style_key", "style_web_standard"),
                concept=ctx.concept,
                title=ctx.title,
                cheat_scale=p_settings.get("cheat_scale", 4),
                growth_curve=p_settings.get("growth_curve", "最初からカンスト(無双)"),
                system_assist=p_settings.get("system_assist", 70),
                cost_severity=p_settings.get("cost_severity", 2),
                target_eps=ctx.target_eps,
                initial_plot_limit=3,
                reporter=reporter,
            )
            ctx.book_id = book_id
            ctx.title = bible.title

            # Store easy parameters for visualization and transition
            ctx.easy_parameters = {
                "genre": ctx.genre,
                "archetype": ctx.archetype_key,
                "style_key": p_settings.get("style_key", "style_web_standard"),
                "cheat_scale": p_settings.get("cheat_scale", 4),
                "system_assist": p_settings.get("system_assist", 70),
                "cost_severity": p_settings.get("cost_severity", 2),
                "target_eps": ctx.target_eps,
                "concept": ctx.concept,
                "tone_vibe": ctx.tone_vibe
            }

            # P1-16: Store catharsis pattern info for visualization
            try:
                if hasattr(bible, 'catharsis_pattern') and bible.catharsis_pattern:
                    ctx.easy_parameters["catharsis_pattern"] = (
                        bible.catharsis_pattern.model_dump()
                        if hasattr(bible.catharsis_pattern, 'model_dump')
                        else dict(bible.catharsis_pattern)
                    )
                elif isinstance(bible, dict) and 'catharsis_pattern' in bible:
                    ctx.easy_parameters["catharsis_pattern"] = bible['catharsis_pattern']
                elif isinstance(bible, dict) and 'catharsis_positions' in bible:
                    ctx.easy_parameters["catharsis_positions"] = bible['catharsis_positions']
            except Exception:
                pass  # Silent fail for visualization

            # 健全性チェック
            if engine.planner.plan_auditor and not await engine.planner.plan_auditor.audit_bible_completeness(bible, reporter=reporter):
                # We stop the pipeline
                return False

            if reporter.state.should_stop():
                return False
            return True
        except Exception as e:
            reporter.report(f"🚨 企画生成中にエラーが発生しました: {e}. APIキーや入力設定を確認してください。", "error")
            raise

class WriteStep(WorkflowStep):
    async def execute(self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter) -> bool:
        if ctx.book_id is None:
            return False
        try:
            reporter.update_progress(1, 3, "STEP 2/3: 本文を自動執筆中...")
            chars_count, failed_episodes = await engine.writer.generate_episodes_pipeline(
                book_id=ctx.book_id,
                start_ep=1,
                end_ep=ctx.target_eps,
                passion=ctx.tone_vibe,
                target_word_count=ctx.word_count,
                reporter=reporter,
                is_easy_mode=True
            )
            ctx.chars_count = chars_count
            ctx.failed_episodes = failed_episodes

            # 自動再試行 (失敗したエピソードのみをピンポイントで再試行)
            if failed_episodes and not reporter.state.should_stop():
                err_details = " / ".join([f"第{f.get('ep_num', '?')}話: {f.get('error_message', '不明')}" for f in failed_episodes])
                reporter.report(f"🔄 {len(failed_episodes)}件のエピソードで不備を検知 ({err_details})。ピンポイント修復中...", "warning")

                # 失敗したエピソードの範囲を特定し、その範囲のみを再生成
                failed_eps_nums = [f.get('ep_num') for f in failed_episodes if f.get('ep_num')]
                if failed_eps_nums:
                    start_retry = min(failed_eps_nums)
                    end_retry = max(failed_eps_nums)
                    retry_chars, still_failed = await engine.writer.generate_episodes_pipeline(
                        book_id=ctx.book_id,
                        start_ep=start_retry,
                        end_ep=end_retry,
                        passion=ctx.tone_vibe,
                        target_word_count=ctx.word_count,
                        reporter=reporter,
                        is_easy_mode=True
                    )
                    ctx.chars_count += retry_chars
                    ctx.failed_episodes = still_failed

            if reporter.state.should_stop():
                return False
            return True
        except Exception as e:
            reporter.report(f"🚨 本文執筆中にエラーが発生しました: {e}. プロットやキャラクター設定に問題がないか確認してください。", "error")
            raise

class PackageStep(WorkflowStep):
    async def execute(self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter) -> bool:
        if ctx.book_id is None:
            return False
        try:
            reporter.update_progress(2, 3, "STEP 3/3: 納品データの準備中...")
            # バックグラウンドでのJSONシリアライズエラー(bytes)を回避するため、
            # 実際のZIPデータ生成はフロントエンド（宣伝・納品タブ）で行わせる
            ctx.zip_data = None
            ctx.zip_filename = f"export_{ctx.book_id}.zip"
            reporter.update_progress(3, 3, "全行程完了！")
            return True
        except Exception as e:
            reporter.report(f"🚨 納品データの準備中にエラーが発生しました: {e}", "error")
            raise

class AutoWorkflowPipeline:
    def __init__(self, steps: List[WorkflowStep]):
        self.steps = steps

    async def execute(self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter) -> FullAutoWorkflowResult:
        reporter.report("🚀 全自動モード開始！", "info")

        for step in self.steps:
            success = await step.execute(ctx, engine, reporter)
            if not success:
                status = "stopped" if reporter.state.should_stop() else "failed"
                # If PlanStep failed integrity check, it might have set failed_integrity_check status,
                # let's map it:
                if isinstance(step, PlanStep) and not reporter.state.should_stop():
                    status = "failed_integrity_check"
                return FullAutoWorkflowResult(
                    book_id=ctx.book_id,
                    title=ctx.title,
                    chars_count=ctx.chars_count,
                    failed_episodes=ctx.failed_episodes,
                    status=status,
                    easy_parameters=ctx.easy_parameters
                )

        return FullAutoWorkflowResult(
            book_id=ctx.book_id,
            title=ctx.title,
            chars_count=ctx.chars_count,
            failed_episodes=ctx.failed_episodes,
            zip_data=ctx.zip_data,
            zip_filename=ctx.zip_filename,
            status="success",
            easy_parameters=ctx.easy_parameters
        )
