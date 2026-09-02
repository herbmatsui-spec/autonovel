"""
新規パイプライン Step 実装
FullAutoWorkflow / EasyModePipeline から移植・統合
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.backend.background import StatusReporter
    from src.backend.engine import UltimateHegemonyEngine

from src.services.pipeline_base import WorkflowContext, WorkflowStep
from src.services.audit_adapter import create_audit_adapter
from src.services.preset_loader import (
    get_cheat_scale,
    get_cost_severity,
    get_growth_curve,
    get_plot_pattern,
    get_style_key,
    get_system_assist,
    get_tension_curve,
    load_preset_for_pipeline,
)
from src.services.spice_guard_adapter import create_spice_guard_adapter
from src.backend.observability.health import metrics

logger = logging.getLogger(__name__)


def _emit_skip(
    reporter: "StatusReporter",
    ctx: WorkflowContext,
    step: str,
    reason: str,
) -> None:
    """Skip 理由を reporter / ctx.warnings / metrics に一発で伝播する。

    - reporter.report(..., "warning"): 既存 UI への通知
    - ctx.warnings.append(...): テスト・運用で検知可能
    - metrics.increment(f"step_skip.{step}"): Prometheus カウンタ
    """
    msg = f"{step}: {reason}"
    try:
        reporter.report(f"⏭️ {msg}", "warning")
    except Exception as e:  # noqa: BLE001
        logger.debug("reporter.report failed in _emit_skip: %s", e)
    ctx.warnings.append(msg)
    try:
        metrics.increment(f"step_skip.{step}")
    except Exception as e:  # noqa: BLE001
        logger.debug("metrics.increment failed in _emit_skip: %s", e)


# ============================================================================
# Step 10-11: PlanStep 拡張 (カタルシス分析・プリセット適用)
# ============================================================================

class PlanStep(WorkflowStep):
    """企画生成 Step (FullAutoWorkflow + EasyMode プリセット統合版)"""

    async def execute(
        self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter
    ) -> bool:
        # 統合プリセット読み込み
        preset = load_preset_for_pipeline(ctx.genre, ctx.archetype_key)

        try:
            reporter.update_progress(0, 4, "STEP 1/4: 覇権企画を生成中...")

            book_id, bible = await engine.planner.create_hegemony_plan(
                genre=ctx.genre,
                keywords=ctx.keywords,
                style_key=get_style_key(preset),
                concept=ctx.concept,
                title=ctx.title,
                cheat_scale=get_cheat_scale(preset),
                growth_curve=get_growth_curve(preset),
                system_assist=get_system_assist(preset),
                cost_severity=get_cost_severity(preset),
                target_eps=ctx.target_eps,
                initial_plot_limit=3,
                enable_erotic=ctx.easy_parameters.get("enable_erotic", False) if ctx.easy_parameters else False,
                erotic_intensity=ctx.easy_parameters.get("erotic_intensity", 2) if ctx.easy_parameters else 2,
                reporter=reporter,
            )
            ctx.book_id = book_id
            ctx.title = bible.title

            # 易パラメータ保存 (可視化・遷移用)
            ctx.easy_parameters = {
                "genre": ctx.genre,
                "archetype": ctx.archetype_key,
                "style_key": get_style_key(preset),
                "cheat_scale": get_cheat_scale(preset),
                "system_assist": get_system_assist(preset),
                "cost_severity": get_cost_severity(preset),
                "target_eps": ctx.target_eps,
                "concept": ctx.concept,
                "tone_vibe": ctx.tone_vibe,
                "preset_name": ctx.preset_name,
            }

            # カタルシスパターン情報保存 (FullAuto 由来)
            if ctx.enable_catharsis_analysis:
                try:
                    from config.project_context import ProjectContext
                    from src.backend.engine_narrative import WavePatternAnalyzer

                    plots = await engine.repo.plot.get_all_plots(book_id)
                    tension_history = [getattr(p, "tension", 50) for p in plots] if plots else [50] * 5

                    wave_analyzer = WavePatternAnalyzer(
                        threshold=ProjectContext.get_setting("catharsis_threshold", 65),
                        reset_value=ProjectContext.get_setting("catharsis_reset_value", 0),
                    )
                    catharsis_pattern = wave_analyzer.analyze(tension_history)

                    if hasattr(bible, "model_dump"):
                        bible_dict = bible.model_dump()
                    else:
                        bible_dict = dict(bible) if not isinstance(bible, dict) else bible

                    bible_dict["catharsis_pattern"] = catharsis_pattern.model_dump()
                    bible_dict["catharsis_positions"] = catharsis_pattern.catharsis_points

                    ctx.catharsis_pattern = catharsis_pattern.model_dump()
                    ctx.catharsis_positions = catharsis_pattern.catharsis_points
                    ctx.easy_parameters["catharsis_pattern"] = catharsis_pattern.model_dump()
                    ctx.easy_parameters["catharsis_positions"] = catharsis_pattern.catharsis_points

                    reporter.report(
                        f"📊 カタルシスパターン分析完了: {len(catharsis_pattern.catharsis_points)}個のカタルシス点を検出",
                        "info",
                    )
                except Exception as e:
                    reporter.report(
                        f"⚠️ カタルシスパターン分析中にエラーが発生しましたが、処理を継続します: {e}",
                        "warning",
                    )

            # 健全性チェック
            if (
                hasattr(engine.planner, "plan_auditor")
                and engine.planner.plan_auditor
                and not await engine.planner.plan_auditor.audit_bible_completeness(bible, reporter=reporter)
            ):
                return False

            if reporter.state.should_stop():
                return False
            return True
        except Exception as e:
            reporter.report(
                f"🚨 企画生成中にエラーが発生しました: {e}. APIキーや入力設定を確認してください。",
                "error",
            )
            raise


# ============================================================================
# Step 12: WriteStep 拡張 (共通リトライロジック使用)
# ============================================================================

class WriteStep(WorkflowStep):
    """本文執筆 Step (共通リトライロジック使用版)"""

    async def execute(
        self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter
    ) -> bool:
        if ctx.book_id is None:
            return False
        try:
            reporter.update_progress(1, 4, "STEP 2/4: 本文を自動執筆中...")

            # 共通リトライロジック使用
            from src.backend.workflows._shared_ops import execute_with_retry

            async def write_operation():
                return await engine.writer.generate_episodes_pipeline(
                    book_id=ctx.book_id,
                    start_ep=1,
                    end_ep=ctx.target_eps,
                    passion=ctx.tone_vibe,
                    target_word_count=ctx.word_count,
                    reporter=reporter,
                    is_easy_mode=ctx.is_easy_mode,
                )

            chars_count, failed_episodes = await execute_with_retry(
                operation=write_operation,
                reporter=reporter,
                max_retries=ctx.max_retries,
                failure_message="エピソードで不備を検知",
                retry_message="ピンポイント修復中...",
            )
            ctx.chars_count = chars_count
            ctx.failed_episodes = failed_episodes

            if reporter.state.should_stop():
                return False
            return True
        except Exception as e:
            reporter.report(
                f"🚨 本文執筆中にエラーが発生しました: {e}. プロットやキャラクター設定に問題がないか確認してください。",
                "error",
            )
            raise


# ============================================================================
# Step 13: CatharsisAnalysisStep (独立 Step 化)
# ============================================================================

class CatharsisAnalysisStep(WorkflowStep):
    """カタルシスパターン分析 Step (FullAuto 由来・独立化)"""

    async def execute(
        self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter
    ) -> bool:
        if not ctx.enable_catharsis_analysis:
            _emit_skip(reporter, ctx, "catharsis", "enable_catharsis_analysis=False")
            return True
        if ctx.book_id is None:
            _emit_skip(reporter, ctx, "catharsis", "book_id is None")
            return True

        try:
            reporter.report("📊 カタルシスパターンを詳細分析中...", "info")

            from config.project_context import ProjectContext
            from src.backend.engine_narrative import WavePatternAnalyzer

            plots = await engine.repo.plot.get_all_plots(ctx.book_id)
            tension_history = [getattr(p, "tension", 50) for p in plots] if plots else [50] * 5

            wave_analyzer = WavePatternAnalyzer(
                threshold=ProjectContext.get_setting("catharsis_threshold", 65),
                reset_value=ProjectContext.get_setting("catharsis_reset_value", 0),
            )
            catharsis_pattern = wave_analyzer.analyze(tension_history)

            ctx.catharsis_pattern = catharsis_pattern.model_dump()
            ctx.catharsis_positions = catharsis_pattern.catharsis_points
            ctx.easy_parameters["catharsis_pattern"] = catharsis_pattern.model_dump()
            ctx.easy_parameters["catharsis_positions"] = catharsis_pattern.catharsis_points

            reporter.report(
                f"📊 カタルシス分析完了: {len(catharsis_pattern.catharsis_points)}点検出 "
                f"(タイプ: {catharsis_pattern.pattern_type}, 振幅: {catharsis_pattern.amplitude:.1f})",
                "info",
            )
            return True
        except Exception as e:
            reporter.report(f"⚠️ カタルシス分析エラー (継続): {e}", "warning")
            return True  # 失敗してもパイプライン継続


# ============================================================================
# Step 14: AuditRewriteStep (核心: EasyMode の監査リライト循環)
# ============================================================================

class AuditRewriteStep(WorkflowStep):
    """
    監査→リライト循環 Step (EasyModePipeline._generate_episode 由来)
    - エピソードごとに監査実施
    - 目標スコア未達なら SpiceGuard 保護付きでリライト
    - max_rewrite_iterations 回まで繰り返し
    """

    async def execute(
        self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter
    ) -> bool:
        if not ctx.enable_spice_guard:
            logger.info("SpiceGuard 無効: AuditRewriteStep をスキップ")
            return True
        if ctx.book_id is None:
            return True

        audit_adapter = create_audit_adapter(engine)
        spice_guard = create_spice_guard_adapter(ctx.genre)

        total_score = 0.0
        episode_details = []

        for ep_num in range(1, ctx.target_eps + 1):
            if reporter.state.should_stop():
                return False

            reporter.update_progress(2, 4, f"STEP 3/4: 第{ep_num}話 監査・リライト中... ({ep_num}/{ctx.target_eps})")

            try:
                # 1. エピソード本文取得
                episode_data = await engine.repo.episode.get_by_book_and_number(ctx.book_id, ep_num)
                if not episode_data or not episode_data.content:
                    logger.warning(f"Episode {ep_num} content not found, skipping audit")
                    continue

                content = episode_data.content

                # 2. プロット・Bible 取得 (監査コンテキスト用)
                bible = await engine.repo.bible.get_by_book_id(ctx.book_id)
                plot = await engine.repo.plot.get_by_book_and_number(ctx.book_id, ep_num)

                audit_context = {
                    "bible": bible.__dict__ if hasattr(bible, "__dict__") else bible,
                    "plot": plot.__dict__ if hasattr(plot, "__dict__") else plot,
                    "episode": ep_num,
                    "genre": ctx.genre,
                    "target_audit_score": ctx.target_audit_score,
                }

                # 3. 初回監査
                audit_result = await audit_adapter.audit_episode(content, audit_context)

                # 4. リライトループ
                final_content = content
                rewrite_count = 0
                spice_elements = []

                if ctx.enable_spice_guard:
                    spice_elements = spice_guard.extract_spice(content)

                for rewrite_iter in range(ctx.max_rewrite_iterations):
                    if audit_result["score"] >= ctx.target_audit_score:
                        break

                    if rewrite_iter >= ctx.max_rewrite_iterations - 1:
                        audit_result["needs_human_review"] = True
                        break

                    # 改善指示でリライト
                    improvements = audit_result.get("improvements", [])
                    if not improvements:
                        break

                    rewrite_prompt = spice_guard.build_rewrite_prompt(final_content, improvements, spice_elements)

                    try:
                        rewritten = await engine.llm.generate(rewrite_prompt, {})
                        if rewritten and rewritten.strip():
                            final_content = spice_guard.clean_markers(rewritten)
                            # 再監査
                            audit_result = await audit_adapter.audit_episode(final_content, audit_context)
                            rewrite_count += 1
                        else:
                            break
                    except Exception as e:
                        logger.warning(f"Rewrite failed for ep {ep_num}: {e}")
                        break

                # 5. 最終本文を DB 更新
                if final_content != content:
                    await engine.repo.episode.update_content(ctx.book_id, ep_num, final_content)

                # 6. 結果記録
                total_score += audit_result["score"]
                episode_details.append({
                    "episode_num": ep_num,
                    "audit_score": audit_result["score"],
                    "audit_passed": audit_result["score"] >= ctx.target_audit_score,
                    "rewrite_count": rewrite_count,
                    "needs_human_review": audit_result.get("needs_human_review", False),
                    "spice_count": len(spice_elements),
                })

            except Exception as e:
                logger.error(f"AuditRewrite failed for ep {ep_num}: {e}")
                episode_details.append({
                    "episode_num": ep_num,
                    "audit_score": 0.0,
                    "audit_passed": False,
                    "rewrite_count": 0,
                    "needs_human_review": True,
                    "error": str(e),
                })

        # 平均スコア計算・保存
        if episode_details:
            ctx.average_audit_score = round(total_score / len(episode_details), 1)
        ctx.episodes_detail = episode_details
        # ctx.spice_guard_enabled は WorkflowContext にフィールドがないため削除
        # 代わりに easy_parameters に記録
        ctx.easy_parameters["spice_guard_enabled"] = True

        reporter.report(
            f"✅ 監査・リライト完了: 平均スコア {ctx.average_audit_score:.1f}, "
            f"通過 {sum(1 for e in episode_details if e['audit_passed'])}/{len(episode_details)}話",
            "info",
        )
        return True


# ============================================================================
# Step 15: PackageStep 拡張
# ============================================================================

class PackageStep(WorkflowStep):
    """納品パッケージ準備 Step (結果集約拡張版)"""

    async def execute(
        self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter
    ) -> bool:
        if ctx.book_id is None:
            _emit_skip(reporter, ctx, "package", "book_id is None")
            return False
        try:
            reporter.update_progress(3, 4, "STEP 4/4: 納品データの準備中...")

            # ZIP生成はフロントエンドで行うため None
            ctx.zip_data = None
            ctx.zip_filename = f"export_{ctx.book_id}.zip"

            # 書籍情報取得
            book = await engine.repo.get_book(ctx.book_id)
            if book:
                ctx.title = book.title

            # marketing_pack が未生成 (enable_marketing=False) でも安全
            if not ctx.marketing_pack:
                ctx.marketing_pack = {
                    "title": ctx.title,
                    "concept": ctx.concept,
                    "synopsis": {},
                    "catchphrase": "",
                    "tags": [],
                }
                _emit_skip(
                    reporter,
                    ctx,
                    "package",
                    "marketing_pack was empty; filled with default shell",
                )

            reporter.update_progress(4, 4, "全行程完了！")
            return True
        except Exception as e:
            reporter.report(f"🚨 納品データの準備中にエラーが発生しました: {e}", "error")
            raise


# ============================================================================
# Step 16: IllustrationStep (FullAuto 由来)
# ============================================================================

class IllustrationStep(WorkflowStep):
    """挿絵生成 Step (FullAutoWorkflow 由来)"""

    async def execute(
        self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter
    ) -> bool:
        if not ctx.enable_illustration:
            _emit_skip(reporter, ctx, "illustration", "enable_illustration=False")
            return True
        if not ctx.illustration_settings or not ctx.illustration_settings.get("enableIllustration"):
            _emit_skip(reporter, ctx, "illustration", "illustration_settings.enableIllustration is not set")
            return True
        if ctx.book_id is None:
            _emit_skip(reporter, ctx, "illustration", "book_id is None")
            return True

        try:
            reporter.update_progress(3, 4, "挿絵を生成中...", "STEP 3.5/4: イラスト生成")

            from src.backend.workflows.illustration_workflow import IllustrationWorkflow

            # engine.illustration_agent を再利用 (AppContainer と二重管理しない)
            ill_agent = getattr(engine, "illustration_agent", None)
            if ill_agent is None:
                # フォールバック: コンテナ未注入の古い Engine 互換 (テスト用)
                from src.agents.illustration_agent import IllustrationAgent
                from src.services.image_service import ImageService
                import os

                ill_agent = IllustrationAgent(
                    image_service=ImageService(api_key=os.getenv("GOOGLE_GENAI_API_KEY", ""))
                )

            ill_workflow = IllustrationWorkflow(
                illustration_agent=ill_agent,
                repo=engine.repo,
            )

            ill_res = await ill_workflow.execute(
                reporter=reporter, book_id=ctx.book_id, settings=ctx.illustration_settings
            )
            if ill_res.get("status") == "success":
                ctx.illustrations = ill_res.get("illustrations", [])
                reporter.report(f"🎨 挿絵生成完了: {len(ctx.illustrations)}枚", "info")
            else:
                reporter.report(f"⚠️ 挿絵生成に失敗: {ill_res.get('error', '不明')}", "warning")

            return True
        except Exception as e:
            reporter.report(f"⚠️ 挿絵生成中にエラーが発生しましたが、作品は完成しています: {e}", "warning")
            return True  # 挿絵失敗でも本編は継続


# ============================================================================
# Step 17: MarketingStep (EasyMode _finalize_series 由来)
# ============================================================================

class MarketingStep(WorkflowStep):
    """マーケティング情報生成 Step (タイトル・あらすじ・キャッチコピー)

    タイトルは 3 段フォールバック:
      1) プリセット (titles.title_templates[0])
      2) LLM (engine.llm.generate)
      3) 固定テンプレ (f"{genre}の物語")
    """

    async def execute(
        self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter
    ) -> bool:
        if not ctx.enable_marketing:
            _emit_skip(reporter, ctx, "marketing", "enable_marketing=False")
            return True
        if ctx.book_id is None:
            _emit_skip(reporter, ctx, "marketing", "book_id is None")
            return True

        try:
            reporter.report("📢 マーケティング情報を生成中...", "info")

            # プリセットからマーケティング情報取得 (archetype_key 未設定も安全)
            archetype = ctx.archetype_key or "default"
            preset = load_preset_for_pipeline(ctx.genre, archetype) or {}
            marketing = preset.get("marketing") or {}
            titles = preset.get("titles") or {}

            # === 1段: プリセット ===
            title_templates = titles.get("title_templates") or []
            if not ctx.title and title_templates:
                ctx.title = title_templates[0]

            # === 2段: LLM (タイトル未設定時のみ) ===
            if not ctx.title:
                try:
                    llm_prompt = (
                        f"以下のコンセプトから魅力的な日本語の Web 小説タイトルを 1 行で提案してください。\n"
                        f"ジャンル: {ctx.genre}\n"
                        f"コンセプト: {ctx.concept or '(なし)'}\n"
                        f"タイトル以外の文章は出力しないでください。"
                    )
                    res = await engine.llm.generate(llm_prompt, {})
                    candidate = (res or "").strip().split("\n")[0].strip().strip("「」『』\"'")
                    if candidate:
                        ctx.title = candidate[:80]
                except Exception as e:
                    logger.debug("MarketingStep LLM fallback failed: %s", e)

            # === 3段: 固定テンプレ ===
            if not ctx.title:
                ctx.title = f"{ctx.genre}の物語"

            # あらすじ・キャッチコピー・タグ生成
            synopsis = marketing.get("synopsis_structure") or {}
            catchphrase_templates = marketing.get("catchphrase_templates") or [""]
            tags = (marketing.get("tags") or [])[:10]

            ctx.marketing_pack = {
                "title": ctx.title,
                "concept": synopsis.get("hook") or ctx.concept,
                "synopsis": synopsis,
                "catchphrase": catchphrase_templates[0] if catchphrase_templates else "",
                "tags": tags,
            }

            # easy_parameters にも反映 (フロントエンド表示用)
            ctx.easy_parameters.update({
                "title": ctx.title,
                "catchphrase": ctx.marketing_pack["catchphrase"],
                "tags": tags,
            })

            reporter.report(f"📢 マーケティング生成完了: タイトル『{ctx.title}』", "info")
            return True
        except Exception as e:
            reporter.report(f"⚠️ マーケティング生成エラー (継続): {e}", "warning")
            return True