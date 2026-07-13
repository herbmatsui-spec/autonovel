import json
from typing import Any, Dict, List, Optional

from src.models import PlotEpisode

# ADDED: 監査機能と型定義のインポート
# from src.agents.audit import PlotIntegrityMonitor
from src.models.audit import LogicalAuditIssueList


class PlanningAgentRebuildMixin:
    """
    PlanningAgentなどにMix-inして使用する、プロット再構築機能の実装。
    指定話数以降の展開を、過去の文脈を考慮した上で新しい方向性に基づいて再生成します。
    """

    async def rebuild_hegemony_plot(
        self,
        book_id: int,
        start_ep: int,
        new_total: int,
        new_keywords: str,
        trend_memo: str,
        plot_pattern: str,
        cheat_scale: int,
        cost_severity: int,
        system_assist: int,
        reporter: Optional[Any] = None
    ) -> List[PlotEpisode]:

        if reporter:
            reporter.report(f"🔨 第{start_ep}話以降のプロット再構築を開始します...", "info")

        # --- 準備フェーズ ---
        book = await self.engine.repo.get_book(book_id)
        if not book:
            if reporter: reporter.report("作品が見つかりません。", "error")
            return []

        bible = await self.engine.repo.get_latest_bible(book_id)
        if not bible:
            if reporter: reporter.report("作品の世界観設定（Bible）が見つかりません。", "error")
            return []

        settings = self._safe_get_dict(bible.settings if bible and hasattr(bible, "settings") else None)
        world_settings_str = json.dumps(settings, ensure_ascii=False)

        branch_id = book.current_branch_id or 1

        # 1. 過去の確定済みプロットのコンテキストを取得
        past_plots = await self.engine.repo.get_plots_between(branch_id, 1, start_ep - 1)
        past_context = "\n".join([f"- 第{p.ep_num}話: {p.summary}" for p in past_plots]) if past_plots else "過去の文脈なし"

        # 2. 新しい方向性に基づき、全体アークを再設計
        # ※ prompt manager に build_rebuild_arc_prompt が定義されている想定です
        arc_prompt = self.engine.pm.build_rebuild_arc_prompt(
            past_context=past_context,
            new_keywords=new_keywords,
            trend_memo=trend_memo,
            plot_pattern=plot_pattern,
            new_total=new_total,
            start_ep=start_ep
        )

        if reporter:
            reporter.report("新しい物語アーク(展開の方向性)を再設計中...", "info")

        arc_result = await self.engine.llm.generate_json(
            prompt=arc_prompt,
            response_schema=Dict[str, Any], # 実際のスキーマに置き換えてください（例: ArcList）
            reporter=reporter
        )

        if not arc_result.success:
            if reporter: reporter.report(f"アークの再設計に失敗しました: {arc_result.error_message}", "error")
            return []

        new_plots: List[PlotEpisode] = []
        # 3. 個別のプロット生成と監査ループ
        for ep_num in range(start_ep, new_total + 1):
            if reporter:
                reporter.update_progress(ep_num - start_ep, new_total - start_ep + 1, f"第{ep_num}話のプロットを再構築中")

            plot_prompt = self.engine.pm.build_expansion_prompt(
                title=book.title,
                ep_num=ep_num,
                arc_metadata=arc_result.metadata,
                past_context=past_context
            )

            max_retries = 3
            last_error_summary = ""
            plot_data = None

            for attempt in range(max_retries):
                current_prompt = plot_prompt
                if attempt > 0 and last_error_summary:
                    current_prompt += f"\n\n【⚠️前回の生成における監査エラー（修正指示）】\n以下のエラーを解消するようにプロットを修正してください：\n{last_error_summary}"

                plot_result = await self.engine.llm.generate_json(
                    prompt=current_prompt,
                    response_schema=PlotEpisode,
                    reporter=reporter,
                    expected_ep_num=ep_num
                )

                if not plot_result.success:
                    if reporter: reporter.report(f"第{ep_num}話の生成に失敗しました: {plot_result.error_message}", "warning")
                    continue

                plot_data = PlotEpisode.model_validate(plot_result.metadata)

                # --- 監査フェーズ ---
                if reporter:
                    reporter.report(f"⚖️ 第{ep_num}話: 生成されたプロットの監査を実行中... (試行 {attempt + 1}/{max_retries})", "info")

                # 監査1: 論理整合性 (LogicalAuditor)
                logical_audit_issues: LogicalAuditIssueList = await self.engine.auditor.audit_plot_as_issues(
                    book_id=book_id,
                    branch_id=branch_id,
                    ep_num=ep_num,
                    plot_bp=plot_data.detailed_blueprint
                )

                # 監査2: 世界観・因果律整合性 (PlotIntegrityMonitor)
                monitor = PlotIntegrityMonitor(pm=self.engine.pm, llm=self.engine.llm)
                is_causal_ok, causal_reason, failures = await monitor.audit_setting_causality(
                    content=plot_data.detailed_blueprint,
                    world_settings=world_settings_str,
                    plot_blueprint=plot_data.detailed_blueprint
                )

                if logical_audit_issues.is_consistent and is_causal_ok:
                    if reporter:
                        reporter.report(f"✅ 第{ep_num}話: 監査合格", "success")
                    break  # 成功した場合はリトライループを抜ける
                else:
                    error_messages = []
                    if not logical_audit_issues.is_consistent:
                        error_messages.extend([i.description for i in logical_audit_issues.issues])
                    if not is_causal_ok:
                        error_messages.append(causal_reason)

                    last_error_summary = ", ".join(error_messages)
                    if reporter:
                        reporter.report(f"⚠️ 第{ep_num}話: 監査で問題を検知しました。自動修復を試みます...: {last_error_summary}", "warning")

                    # 最後の試行だった場合はプロットに警告を追記
                    if attempt == max_retries - 1:
                        plot_data.lite_model_director_notes = f"【監査警告(未解決)】{last_error_summary}\n{plot_data.lite_model_director_notes or ''}"

            if plot_data:
                new_plots.append(plot_data)

        # 4. トランザクションと状態の永続化
        if new_plots:
            try:
                async with self.engine.uow:
                    if reporter:
                        reporter.report(f"💾 データベースを更新中... (第{start_ep}話以降の古いプロットをアーカイブし、新しいプロットを保存します)", "info")

                    # 古いプロットをアーカイブ (または削除)。リポジトリにこの実装が必要です。
                    await self.engine.repo.archive_plots_from(branch_id, start_ep, new_total)

                    # 新しいプロットを保存
                    for plot in new_plots:
                        await self.engine.repo.save_plot(branch_id, plot.ep_num, plot)

                if reporter:
                    reporter.report("✅ プロットの再構築と保存が完了しました！", "success")

            except Exception as e:
                if reporter:
                    reporter.report(f"🚨 データベースの更新中にエラーが発生しました: {e}", "error")
                # UnitOfWork のコンテキストマネージャがロールバックを処理します
                return []

        return new_plots

