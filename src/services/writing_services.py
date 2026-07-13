import json
import logging
import uuid
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel

from config.project_context import ProjectContext
from src.agents.audit import PlotIntegrityMonitor
from src.models import WritingContext

logger = logging.getLogger(__name__)

class WritingGenerationContext(BaseModel):
    sys_inst: str = ""
    fw_prompt: str = ""
    pov_instruction: str = ""
    expanded_beats: str = ""
    feedback_patch: str = ""
    style_key: str = "style_web_standard"
    target_word_count: int = 2000
    enable_polishing: bool = True
    prose_sample: str = ""
    plot: Optional[Any] = None


    def build_sys_inst(self) -> str:
        parts = [self.sys_inst]
        if self.pov_instruction: parts.append(self.pov_instruction)
        if self.feedback_patch: parts.append(f"\n\n【🚨自己評価フィードバックパッチ】\n{self.feedback_patch}")
        return "\n\n".join(parts)

    def build_fw_prompt(self, suffix: str = "") -> str:
        parts = [self.fw_prompt]
        if self.pov_instruction: parts.append(self.pov_instruction)
        if self.expanded_beats: parts.append(f"\n\n【📝 物理動作ビート分解（絶対遵守）】\n以下のビートに従って、各ビートの文字数を意識しShow, Don't Tellを徹底しながら執筆してください：\n{self.expanded_beats}\n")
        if suffix: parts.append(suffix)
        return "\n\n".join(parts)


class GenerationLoopManager:
    def __init__(self, repo, llm, pm, critique, narrative, config):
        self.repo = repo
        self.llm = llm
        self.pm = pm
        self.critique = critique
        self.narrative = narrative
        self.config = config

    async def execute_generation_loop(self, ep_num: int, ctx: WritingContext, sys_inst: str, fw_prompt: str, passion: float, is_easy_mode: bool, reporter) -> Tuple[str, Dict[str, Any], bool]:
        trace_id = str(uuid.uuid4())
        logger.info(f"[Trace {trace_id}] Starting generation loop for Ep.{ep_num}")

        gen_ctx, should_dogfeed, should_heavy_audit, should_beat_decompose, ncs_score = await self._phase_prepare_context(
            ep_num, ctx, sys_inst, fw_prompt, is_easy_mode, reporter
        )

        # 動的バジェット管理: 重要度が低い通常回はループを1回に制限
        base_max_ac_iter = ProjectContext.get_setting("actor_critic_max_iterations", 2)
        max_ac_iter = 1 if ncs_score < 40 else base_max_ac_iter
        if reporter and max_ac_iter == 1:
            reporter.report(f"ℹ️ 第{ep_num}話: 通常回のため、Actor-Criticの反復回数を {max_ac_iter} に制限し、スパイクを物理的に防ぎます。", "info")

        final_content, final_meta, is_integrity_ok = "", {}, True
        is_causal_ok, causal_reason, failures = True, "", []
        rate = 1.0
        blueprint = ctx["plot"].detailed_blueprint or ""
        engine_key = ctx.get("engine_key", "unknown")

        monitor = PlotIntegrityMonitor(self.pm, self.llm)

        threshold = self.narrative.get_integrity_threshold(ctx["genre_str"], ctx.get("prev_integrity", 100), engine_key=engine_key)
        fail_fast = ProjectContext.get_setting("fail_fast_mode", False)

        for ac_iter in range(max_ac_iter):
            temp = 0.7 + (passion - 0.5) * 0.2 + (ac_iter * 0.1)
            logger.info(f"[Trace {trace_id}] Generating (AC Iter {ac_iter+1}/{max_ac_iter}, Engine: {engine_key}, Temp: {temp:.2f})")

            final_content, final_meta = await self._phase_drafting(
                ep_num, blueprint, temp, should_beat_decompose, gen_ctx, reporter
            )
            if not final_content:
                if fail_fast:
                    raise RuntimeError(f"[Trace {trace_id}] Fail-Fast: Drafting yielded empty content.")
                continue

            is_integrity_ok, rate, is_causal_ok, causal_reason, failures = await self._phase_audit(
                ep_num, ctx, final_content, final_meta, blueprint, threshold, should_heavy_audit, monitor
            )

            all_ok = is_integrity_ok and is_causal_ok
            if all_ok or is_easy_mode:
                break

            if should_heavy_audit and not is_easy_mode and ac_iter < max_ac_iter - 1:
                critic_triggered = await self._phase_critic(
                    ac_iter, ep_num, final_content, blueprint, failures, gen_ctx, reporter
                )
                if not critic_triggered:
                    break
            else:
                break

        # 外科的修復（最終フォールバック）
        if should_heavy_audit and not is_causal_ok and not is_easy_mode:
            final_content, is_causal_ok, causal_reason = await self._phase_healing(
                ep_num, final_content, ctx, blueprint, causal_reason, failures, monitor
            )
            if not is_causal_ok and fail_fast:
                raise RuntimeError(f"[Trace {trace_id}] Fail-Fast: Causality validation failed after healing. 指記矛盾: {causal_reason}")

        dogfeed_ok = await self._run_dogfeeding_loop(
            ep_num, final_content, passion, 0.7, should_dogfeed, max_ac_iter - 1, max_ac_iter, gen_ctx, reporter
        )

        if (is_integrity_ok and is_causal_ok and dogfeed_ok) or is_easy_mode:
            logger.info(f"[Trace {trace_id}] Ep.{ep_num} generation successful (Integrity: {rate:.2f}, Causality: {is_causal_ok})")
        else:
            if fail_fast:
                raise RuntimeError(f"[Trace {trace_id}] Fail-Fast: Post-generation loops failed. Integrity={is_integrity_ok}, Causal={is_causal_ok}, Dogfeed={dogfeed_ok}")
            await self._register_lazy_patch(ep_num, ctx, is_integrity_ok, rate, threshold, is_causal_ok, causal_reason, dogfeed_ok, reporter)

        # --- Narrative Metrics Scoring Integration ---
        try:
            from src.agents.audit import LogicalAuditor
            from src.backend.database.repositories.narrative_metrics_repo import (
                NarrativeMetricRepository,
            )

            auditor = LogicalAuditor(self.repo, self.pm, self.llm.generate_json, None)
            metrics_repo = NarrativeMetricRepository(self.repo.session)

            book_id = ctx["book"].id if hasattr(ctx["book"], "id") else ctx["book"].book_id
            branch_id = ctx.get("branch_id", 1)

            scored_scores = await auditor.score_narrative_metrics(
                book_id=book_id,
                branch_id=branch_id,
                ep_num=ep_num,
                scene_num=1,
                scene_content=final_content,
                context=blueprint,
                reporter=reporter,
            )
            await metrics_repo.save_scene_metrics(
                book_id=book_id,
                branch_id=branch_id,
                ep_num=ep_num,
                scene_num=1,
                scores=scored_scores,
            )
            if reporter:
                reporter.report(f"📊 第{ep_num}話のナラティブ指標を保存しました。", "success")

            immersion_score = next((s.get("score", 0.0) for s in scored_scores if s.get("metric_name") == "immersion_score"), 0.0)
            if not is_easy_mode:
                from config.project_context import ProjectContext
                min_immersion = float(ProjectContext.get_setting("min_immersion_score", 0.0) or 0.0)
                if immersion_score < min_immersion and fail_fast:
                    raise RuntimeError(f"Fail-Fast: 没入スコア {immersion_score:.1f} >= {min_immersion} を満たしません。")
                if immersion_score < min_immersion and reporter:
                    reporter.report(f"⚠️ 没入スコア {immersion_score:.1f} が閾値 {min_immersion} 未満です。", "warning")

        except Exception as e:
            logger.error(f"Narrative scoring integration failed: {e}")
            if reporter:
                reporter.report(f"❌ ナラティブ指標の算出中にエラーが発生しました: {e}", "error")

        return final_content, final_meta, is_integrity_ok


    async def _phase_prepare_context(self, ep_num: int, ctx: WritingContext, sys_inst: str, fw_prompt: str, is_easy_mode: bool, reporter) -> Tuple[WritingGenerationContext, bool, bool, bool, int]:
        current_tension = ctx.get("current_tension", 0)
        is_catharsis = getattr(ctx.get("plot"), "is_catharsis", False)

        # style_key and write_rule_type extraction
        style_dna_dict = json.loads(ctx["book"].style_dna) if isinstance(ctx["book"].style_dna, str) else (ctx["book"].style_dna or {})
        style_key = str(style_dna_dict.get("mode", "style_web_standard"))

        prose_samples = ctx.get("prose_samples", [])
        prose_sample = prose_samples[0] if prose_samples else ""

        pov_instruction = self._determine_pov_instruction(ep_num, current_tension, is_catharsis, reporter)
        gen_ctx = WritingGenerationContext(
            sys_inst=sys_inst,
            fw_prompt=fw_prompt,
            pov_instruction=pov_instruction,
            style_key=style_key,
            target_word_count=ctx.get("target_word_count", 2000),
            enable_polishing=not is_easy_mode,
            prose_sample=prose_sample,
            plot=ctx.get("plot")
        )


        ncs_score = self._calculate_ncs_score(ep_num, ctx)
        should_dogfeed = ncs_score >= 50
        should_heavy_audit = ncs_score >= 40
        should_beat_decompose = ncs_score >= 40

        return gen_ctx, should_dogfeed, should_heavy_audit, should_beat_decompose, ncs_score

    async def _phase_drafting(self, ep_num: int, blueprint: str, temp: float, should_beat_decompose: bool, gen_ctx: WritingGenerationContext, reporter) -> Tuple[str, Dict[str, Any]]:
        expanded_beats = ""
        if should_beat_decompose:
            expanded_beats = await self._expand_scene_beats(ep_num, blueprint, temp, reporter)
        else:
            if reporter:
                reporter.report(f"ℹ️ 第{ep_num}話: 標準エピソードのため、ビート分解をスキップしAPIコストを削減します（高速執筆）。", "info")

        gen_ctx.expanded_beats = expanded_beats

        raw_content = await self._draft_episode_parts(ep_num, gen_ctx, temp, reporter)
        if not raw_content:
            return "", {}

        do_polish = gen_ctx.enable_polishing and should_beat_decompose
        if not do_polish and ProjectContext.get_setting("fallback_polish_in_easy_mode", False):
            do_polish = True

        if do_polish and ProjectContext.get_setting("draft_polish_enabled", True):
            use_beat_rules = bool(gen_ctx.expanded_beats)
            final_content = await self._polishing_pass(ep_num, raw_content, gen_ctx, temp, reporter, use_beat_rules=use_beat_rules)
        else:
            final_content = raw_content

        final_meta = await self._extract_episode_metadata(ep_num, final_content, blueprint, temp)
        return final_content, final_meta

    async def _phase_audit(self, ep_num: int, ctx: WritingContext, final_content: str, final_meta: Dict[str, Any], blueprint: str, threshold: float, should_heavy_audit: bool, monitor) -> Tuple[bool, float, bool, str, List[Dict[str, Any]]]:
        is_integrity_ok, rate, _ = await monitor.check_integrity(monitor.extract_keywords(blueprint), blueprint, final_content, threshold=threshold)
        is_causal_ok, causal_reason, failures = await self._run_causality_audits(
            ep_num, ctx, final_content, blueprint, should_heavy_audit, monitor
        )

        from src.agents.state_validator import (
            CharacterStatusChange,
            EpisodeStatusChanges,
            StateContradictionError,
            StateValidator,
        )
        try:
            status_changes = final_meta.get("character_status_changes", []) if final_meta else []
            normalized_changes = []
            for item in status_changes:
                if isinstance(item, dict):
                    normalized_changes.append(CharacterStatusChange(**item))
                elif isinstance(item, CharacterStatusChange):
                    normalized_changes.append(item)

            changes_obj = EpisodeStatusChanges(character_status_changes=normalized_changes)
            prev_ws = ctx.get("prev_world_state") or {}
            StateValidator.validate_transitions(prev_ws, changes_obj)
        except StateContradictionError as e:
            logger.warning(f"Deterministic state verification failed: {e}")
            is_causal_ok = False
            causal_reason = f"【確定ステータス不整合】{str(e)}\n{causal_reason}"
            failures.append({
                "rule": "確定ステータス不整合",
                "gap": str(e),
                "fragment": "ステータス検証エラー"
            })

        return is_integrity_ok, rate, is_causal_ok, causal_reason, failures


    async def _phase_healing(self, ep_num: int, content: str, ctx: WritingContext, blueprint: str, causal_reason: str, failures: List[Dict[str, Any]], monitor) -> Tuple[str, bool, str]:
        return await self._apply_surgical_healing(ep_num, content, ctx, blueprint, causal_reason, failures, monitor)

    async def _phase_critic(
        self,
        ac_iter: int,
        ep_num: int,
        draft_content: str,
        blueprint: str,
        failures: List[Dict[str, Any]],
        gen_ctx: WritingGenerationContext,
        reporter,
    ) -> bool:
        """
        [Actor-Critic] Criticエージェントが修正指示を生成し、
        gen_ctx.feedback_patch に注入する。
        True = 次ループで再執筆すべき指摘あり
        False = スキップ（軽微な矛盾 or Critic無効）
        """
        from config import get_config
        from src.agents.audit import LogicalAuditor
        from src.models.audit import AuditIssue, LogicalAuditIssueList

        cfg = get_config()
        if not ProjectContext.get_setting("actor_critic_enabled", True):
            return False

        # 警告レベルの「メタ階層化」によるフィルタリング: 閾値を設定から取得（デフォルト: Critical）
        threshold = ProjectContext.get_setting("actor_critic_severity_threshold", "Critical")
        severity_rank = {"Critical": 3, "Major": 2, "Minor": 1, "None": 0}

        # failures リストから LogicalAuditIssueList を構築
        issues = []
        for f in failures:
            sev = f.get("severity", "Minor")
            if severity_rank.get(sev, 0) < severity_rank.get(threshold, 3):
                # 軽微な乖離はログ出力のみでスキップ
                if reporter:
                    reporter.report(f"ℹ️ 第{ep_num}話 [Critic Iter {ac_iter+1}]: 軽微な矛盾({sev})を検知しましたが、リライトをトリガーせず進行します。指摘: {f.get('gap', '')}", "info")
                continue
            issues.append(AuditIssue(
                category=f.get("rule", "場所"),
                severity=sev,
                description=f.get("gap", "矛盾あり"),
                evidence_current=f.get("fragment", ""),
            ))

        if not issues:
            return False  # 閾値以上の矛盾なし

        issue_list = LogicalAuditIssueList(
            is_consistent=False,
            issues=issues,
            overall_severity=issues[0].severity,
        )

        if reporter:
            reporter.report(
                f"🎭 第{ep_num}話 [Critic Iter {ac_iter+1}]: "
                f"{len(issues)}件の矛盾を検知。修正指令を生成中...", "warning"
            )

        auditor = LogicalAuditor(
            repo=self.repo,
            llm=self.llm,
            pm=self.pm,
            ctx_mgr=None
        )
        critic_fb = await auditor.generate_critic_feedback(issue_list, draft_content, blueprint)

        if critic_fb.rewrite_guidance:
            gen_ctx.feedback_patch = (
                f"【🚨Critic修正指令（{ac_iter+1}回目）🚨】\n"
                f"{critic_fb.overall_assessment}\n\n"
                f"{critic_fb.rewrite_guidance}"
            )
            if reporter:
                reporter.report(
                    f"🔄 第{ep_num}話 [Actor]: Criticの指示を受け、論理修正を加えてリライトします。", "info"
                )
            return True
        return False


    def _determine_pov_instruction(self, ep_num: int, current_tension: int, is_catharsis: bool, reporter) -> str:
        if current_tension >= 80 or is_catharsis:
            if reporter:
                reporter.report(f"🔄 第{ep_num}話: 幕間・視点変更ロジック（敵の絶望/ヒロインの崇拝）を自動発動しました。", "info")
            return (
                "【🚨特殊割り込み指令：幕間・視点変更（ザマァ/崇拝）🚨】\n"
                "読者のカタルシスを最大化するため、このエピソードは主人公ではなく、外部視点（敵役の絶望、またはヒロイン等の崇拝）をメインに描いてください。\n"
                "主人公の圧倒的な力や知略を外部からの視点で描写し、相対的な『格の違い』を強烈に印象付けること。"
            )
        return ""

    def _calculate_ncs_score(self, ep_num: int, ctx: WritingContext) -> int:
        from config import AUDIT_TRIGGER_KEYWORDS
        summary_text = ((getattr(ctx["plot"], "summary", "") or "") + (getattr(ctx["plot"], "detailed_blueprint", "") or "")).lower()
        ncs_score = 0
        if getattr(ctx["plot"], "is_catharsis", False): ncs_score += 50
        if any(kw in summary_text for kw in AUDIT_TRIGGER_KEYWORDS): ncs_score += 30
        if ep_num <= 3 or ep_num >= (ctx["book"].target_eps or 50) - 2: ncs_score += 30
        return ncs_score

    async def _expand_scene_beats(self, ep_num: int, blueprint: str, temp: float, reporter) -> str:
        if reporter:
            reporter.report(f"🎬 第{ep_num}話: シーン・ビート・エクスパンダーを起動し、プロットを物理動作（Beat）に分解中...", "info")
        # book_id is not readily available in this method, but build_beat_expansion_prompt (if it exists in PromptManager)
        # was previously called without it. Looking at engine_prompts.py, most build_* methods now take book_id.
        # However, _expand_scene_beats doesn't have book_id in its arguments.
        # Let's check if we can get it from elsewhere or if we should pass None.
        beat_prompt = await self.pm.build_beat_expansion_prompt(blueprint, book_id=None)
        beat_res = await self.llm.generate_json(ProjectContext.get_setting("model_writing"), beat_prompt, temp=0.7)
        beat_meta, beat_content = beat_res.unwrap_or({}, "")

        beats_list = []
        if beat_meta and "beats" in beat_meta:
            beats_list = beat_meta["beats"]
        elif beat_content:
            try:
                parsed = json.loads(beat_content)
                if "beats" in parsed: beats_list = parsed["beats"]
            except:
                pass

        if beats_list:
            formatted_beats = []
            for b in beats_list:
                num = b.get("beat_num", "?")
                action = b.get("physical_action", "")
                sensory = ", ".join(b.get("sensory_tags", []))
                phase = b.get("emotion_phase", "")
                budget = b.get("word_budget", 200)
                formatted_beats.append(f"ビート{num}: {action} [五感: {sensory}, フェーズ: {phase}, 目標文字数: {budget}字]")
            if reporter:
                reporter.report(f"✅ 第{ep_num}話: {len(beats_list)}個のビート分解完了。描写の解像度を最大化します。", "success")
            return "\n".join(formatted_beats)
        return beat_content or ""

    async def _draft_episode_parts(self, ep_num: int, gen_ctx: WritingGenerationContext, temp: float, reporter) -> str:
        async def stream_callback(text: str):
            if reporter:
                reporter.update_streaming_text(text)

        if reporter:
            reporter.report(f"📝 第{ep_num}話: 分割執筆（前半）を開始...", "info")

        p1_prompt = gen_ctx.build_fw_prompt("【分割執筆モード：前半】\nこのエピソードの「前半部分（物語 of 導入から中盤の展開まで）」のみを執筆してください。")
        res1 = await self.llm.generate_text(
            ProjectContext.get_setting("model_writing"),
            p1_prompt,
            system_instruction=gen_ctx.build_sys_inst(),
            temp=temp,
            stream_callback=stream_callback
        )
        raw_content1 = res1.story_content if (res1.success and res1.story_content) else ""

        if not raw_content1 or len(raw_content1.strip()) < 50:
            logger.warning(f"Failed to generate part 1 for Ep.{ep_num}")
            return ""

        if reporter:
            reporter.report(f"📝 第{ep_num}話: 分割執筆（後半）を開始...", "info")

        p2_prompt = gen_ctx.build_fw_prompt(f"【分割執筆モード：後半】\n以下の『前半部分』の続きから、エピソードの最後までを執筆してください。前半と同じ内容（重複）は書かず、純粋に続きから再開してください。\n\n=== 前半部分 ===\n{raw_content1}\n================\n")
        res2 = await self.llm.generate_text(
            ProjectContext.get_setting("model_writing"),
            p2_prompt,
            system_instruction=gen_ctx.build_sys_inst(),
            temp=temp,
            stream_callback=stream_callback
        )
        raw_content2 = res2.story_content if (res2.success and res2.story_content) else ""

        if not raw_content2 or len(raw_content2.strip()) < 50:
            logger.warning(f"Failed to generate part 2 for Ep.{ep_num}")
            return ""

        raw_content = raw_content1 + "\n\n" + raw_content2
        return raw_content

    async def _polishing_pass(self, ep_num: int, draft_content: str, gen_ctx: WritingGenerationContext, temp: float, reporter, use_beat_rules: bool = True) -> str:
        """
        初稿に対して品質研磨のみを行う専用パス。
        """
        if reporter:
            reporter.report(f"✨ 第{ep_num}話: 研磨パス（五感・禁止語・リズム・目標文字数）を実行中...", "info")

        plot_data = None
        if gen_ctx.plot:
            if hasattr(gen_ctx.plot, "model_dump"):
                plot_data = gen_ctx.plot.model_dump()
            elif isinstance(gen_ctx.plot, dict):
                plot_data = gen_ctx.plot
            else:
                try:
                    plot_data = dict(gen_ctx.plot)
                except:
                    pass

        polish_prompt = await self.pm.build_polishing_prompt(
            draft_content=draft_content,
            target_word_count=gen_ctx.target_word_count,
            style_key=gen_ctx.style_key,
            prose_sample=gen_ctx.prose_sample,
            plot_data=plot_data,
            use_beat_rules=use_beat_rules,
            book_id=None,
        )


        polish_sys_inst = (
            "あなたは優秀な「推敲エージェント」です。"
            "受け取った【初稿】の物語の流れ・プロット・キャラクターは一切変更せず、"
            "品質改善および文体調整、目標文字数に満たない場合の加筆修正（描写の拡張）のみを行い、"
            "完成稿のみを出力してください。"
        )

        async def stream_callback(text: str):
            if reporter:
                reporter.update_streaming_text(text)

        res = await self.llm.generate_text(
            model_name=ProjectContext.get_setting("model_writing"),
            prompt=polish_prompt,
            system_instruction=polish_sys_inst,
            temp=max(0.4, temp - 0.2),
            stream_callback=stream_callback
        )

        min_ratio = ProjectContext.get_setting("polishing_min_content_ratio", 0.5)
        if res.success and res.story_content and len(res.story_content.strip()) > len(draft_content) * min_ratio:
            if reporter:
                reporter.report(f"✨ 第{ep_num}話: 研磨が完了しました。({len(draft_content)}字 -> {len(res.story_content)}字)", "success")
            return res.story_content

        logger.warning(f"Ep.{ep_num}: Polishing pass failed or produced short output. Using draft.")
        if reporter:
            reporter.report(f"⚠️ 第{ep_num}話: 研磨パスに失敗、または出力が極端に短いため初稿をフォールバックとして採用します。", "warning")
        return draft_content

    async def _extract_episode_metadata(self, ep_num: int, content: str, blueprint: str, temp: float) -> Dict[str, Any]:
        from src.models.writing import EpisodeMetadata
        prompt = (
            f"以下の執筆された小説の本文と、元のプロット設計図を分析し、メタデータを抽出してください。\n\n"
            f"【元のプロット設計図】\n{blueprint}\n\n"
            f"【執筆された本文】\n{content}\n"
        )
        sys_inst = (
            "あなたは優秀な編集者および分析エージェントです。与えられた小説本文とプロットを分析し、"
            "サブタイトル、あらすじ、ストレス値の変化、生活の質（QOL）の変化、好感度の変化、AIインサイト、次の世界状態、および"
            "この話で起きたキャラクターのステータス変更（名前、居場所、生死、所持品の変化）を正確にJSON形式で抽出してください。"
        )

        res = await self.llm.generate_json(
            model_name=ProjectContext.get_setting("model_writing"),
            prompt=prompt,
            response_schema=EpisodeMetadata,
            system_instruction=sys_inst,
            temp=temp
        )
        if res.success and res.metadata:
            return res.metadata
        return {}

    async def _run_causality_audits(self, ep_num: int, ctx: WritingContext, content: str, blueprint: str, should_heavy_audit: bool, monitor) -> Tuple[bool, str, List[Dict[str, Any]]]:
        from config import AUDIT_TRIGGER_KEYWORDS
        is_causal_ok = True
        causal_reason = ""
        failures = []

        if should_heavy_audit and monitor and any(kw in content for kw in AUDIT_TRIGGER_KEYWORDS):
            bible = ctx.get("bible")
            world_settings_str = ""
            active_constraints = []
            if bible:
                settings_dict = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings or "{}")
                world_settings_str = json.dumps(settings_dict, ensure_ascii=False)
                active_constraints = settings_dict.get("active_constraints", [])

            is_causal_ok, causal_reason, failures = await monitor.audit_setting_causality(content, world_settings_str, blueprint)

            if active_constraints:
                tests_ok, test_failures = await monitor.run_constraint_unit_tests(content, active_constraints)
                if not tests_ok:
                    is_causal_ok = False
                    for tf in test_failures:
                        failures.append({
                            'rule': f"制約[{tf.get('constraint_index', '?')}]",
                            'gap': tf.get('reason', '不明'),
                            'fragment': tf.get('violating_snippet', '...')
                        })

            if failures:
                detail_msg = "\n".join([
                    f"・設定項目: {f.get('rule', '共通')}\n  乖離理由: {f.get('gap', '不明')}\n  該当箇所: 『{f.get('fragment', '...')}』"
                    for f in failures
                ])
                causal_reason = f"{causal_reason}\n\n【具体的矛盾の指摘】\n{detail_msg}"

        return is_causal_ok, causal_reason, failures

    async def _apply_surgical_healing(self, ep_num: int, content: str, ctx: WritingContext, blueprint: str, causal_reason: str, failures: List[Dict[str, Any]], monitor) -> Tuple[str, bool, str]:
        logger.info(f"Ep.{ep_num} triggering surgical causality healing...")
        snippets = [f.get('fragment', '') for f in failures if f.get('fragment') and f.get('fragment') != '...']

        bible = ctx.get("bible")
        world_settings_str = ""
        active_constraints = []
        if bible:
            settings_dict = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings or "{}")
            world_settings_str = json.dumps(settings_dict, ensure_ascii=False)
            active_constraints = settings_dict.get("active_constraints", [])

        healed_content = await self.surgical_causality_healing_pass(content, world_settings_str, blueprint, causal_reason, snippets)

        if healed_content:
            if active_constraints:
                recheck_ok, recheck_failures = await monitor.run_constraint_unit_tests(healed_content, active_constraints)
                if recheck_ok:
                    return healed_content, True, ""
                else:
                    logger.warning(f"Surgical healing failed re-audit. {len(recheck_failures)} remaining.")
                    return healed_content, False, "修復後も制約違反が解消されませんでした。"
            else:
                return healed_content, True, ""
        return content, False, causal_reason

    async def _run_dogfeeding_loop(self, ep_num: int, content: str, passion: float, temp: float, should_dogfeed: bool, attempt: int, max_retries: int, gen_ctx: WritingGenerationContext, reporter) -> bool:
        if should_dogfeed and attempt < max_retries - 1:
            eval_result = await self.critique.run_dogfeeding_approval_loop(content, ep_num, passion, temp)
            score = eval_result.get("score", 100)
            if score < 80:
                if reporter:
                    reporter.report(f"⚠️ 第{ep_num}話: 自己評価スコアが低いため({score}点)再生成します。理由: {eval_result.get('reason', '')}", "warning")
                patch = eval_result.get("recommended_patch", "")
                if patch:
                    gen_ctx.feedback_patch = patch
                return False
        elif not should_dogfeed and reporter and attempt == 0:
            reporter.report(f"ℹ️ 第{ep_num}話: 重要度が低いため自己評価(Dogfeeding)をスキップし高速化しました。", "info")
        return True

    async def _register_lazy_patch(self, ep_num: int, ctx: WritingContext, is_integrity_ok: bool, rate: float, threshold: float, is_causal_ok: bool, causal_reason: str, dogfeed_ok: bool, reporter):
        msg = f"Ep.{ep_num} audit failed."
        if not is_integrity_ok:
            msg += f" (Integrity Rate: {rate:.2f} < {threshold})"
        if not is_causal_ok:
            msg += f" (Causality: {causal_reason})"
        if not dogfeed_ok:
            msg += " (Dogfeeding Score too low)"
        logger.warning(f"{msg} [Lazy Patch] 次話以降のプロット・執筆に修正指示（遅延パッチ）を登録し、この話数はそのまま進行します。")

        book_id = ctx["book"].id if hasattr(ctx["book"], "id") else ctx["book"].book_id
        obs = f"第{ep_num}話の執筆において矛盾・品質低下を検知しました。指摘: {msg}"
        corr = "設定制約およびキャラクターの行動原則を絶対遵守し、前話で発生した上記の矛盾を自然に解消・修正する描写を組み込んでください。"
        try:
            # 自動あきらめ＆遅延補正（Lazy Patching の格上げ）
            import time

            from src.models.world import NarrativeConstraint
            latest_bible_model = await self.repo.get_latest_bible(book_id)
            if latest_bible_model:
                settings_dict = latest_bible_model.settings
                if isinstance(settings_dict, str):
                    settings_dict = json.loads(settings_dict)

                active_constraints = settings_dict.get("active_constraints", [])

                # 新しい遅延パッチ制約を作成
                patch_constraint = NarrativeConstraint(
                    subject=f"遅延パッチ(第{ep_num}話由来)",
                    constraint=f"{obs} / {corr}",
                    importance="High"
                )
                active_constraints.append(patch_constraint.model_dump())
                settings_dict["active_constraints"] = active_constraints

                # バイブルを更新して保存
                new_version = (latest_bible_model.version or 0) + 1
                await self.repo.create_bible(book_id, settings_dict, new_version, time.strftime('%Y-%m-%dT%H:%M:%S'))

                if reporter:
                    reporter.report(f"🩹 第{ep_num}話: 矛盾を完全に解消できませんでした。次話以降で自動回収・言い訳を行う「遅延パッチ」をWorldBibleに登録し、強制進行します。", "warning")
            else:
                logger.warning("Could not find latest bible to apply Lazy Patch.")
        except Exception as mem_err:
            logger.error(f"Failed to record Lazy Patch memory: {mem_err}")

    async def surgical_causality_healing_pass(self, content: str, world_settings: str, blueprint: str, failure_reason: str, snippets: List[str] = None) -> str:
        target_content = content
        if snippets and len(snippets) > 0:
            lines = content.split("\n")
            target_lines = []
            for i, line in enumerate(lines):
                if any(s in line for s in snippets):
                    start = max(0, i - 2)
                    end = min(len(lines), i + 3)
                    target_lines.extend(lines[start:end])
            if target_lines:
                target_content = "\n".join(list(dict.fromkeys(target_lines)))

        prompt = self.pm.build_surgical_causality_healing_prompt(target_content, world_settings, blueprint, failure_reason)
        res = await self.llm.generate_text(ProjectContext.get_setting("model_writing"), prompt)

        if res.success and res.story_content:
            if target_content != content:
                old_snippet = target_content.strip()
                new_snippet = res.story_content.strip()
                if old_snippet in content:
                    return content.replace(old_snippet, new_snippet)
            return res.story_content
        return content
