{
  "imports": [
    { "name": "from typing import Any, Dict, List, Optional, TypeVar, Generic, Tuple", "location": "top" },
    { "name": "from datetime import datetime", "location": "top" },
    { "name": "from dataclasses import dataclass", "location": "top" }
  ],
  "types": [
    {
      "name": "RebuildResult",
      "body": """Rebuilderの実行結果を追跡するためのジェネリクエネクスト。
    @dataclass
    class RebuildResult(Generic[T]):
        success: bool = False
        result: Optional[T] = None
        error_message: Optional[str] = None
        timestamp: datetime = None
        metadata: Dict[str, Any] = None""",
      "location": "after imports"
    }
  ],
  "helpers": [
    {
      "name": "_generate_arc_metadata",
      "body": """
    async def _generate_arc_metadata(
        self,
        book_title: str,
        past_context: str,
        new_keywords: str,
        trend_memo: str,
        plot_pattern_key: str,
        new_total: int,
        start_ep: int,
        reporter: Optional[IReporter] = None,
    ) -> Dict[str, Any]:
        """新しいアーク設計方案をLLMで生成する.
        
        Args:
            book_title: 作品のタイトル
            past_context: 過去プロットのコンテキスト
            new_keywords: 新しいキーワード
            trend_memo: トレンドメモ
            plot_pattern_key: プロットパターンキー
            new_total: 新しい総話数
            start_ep: 再構築開始話数
            reporter: レポーター
            
        Returns:
            アークメタデータの辞書
        """
        # プロンプト構築に必要な引数を準備
        prompt = self.pm.build_rebuild_arc_prompt(
            book_title=book_title,
            past_context=past_context,
            new_keywords=new_keywords,
            trend_memo=trend_memo,
            plot_pattern=plot_pattern_key,
            new_total=new_total,
            start_ep=start_ep,
        )

        if reporter:
            reporter.report("新しい物語アーク(展開の方向性)を再設計中...", "info")

        result = await self.generate_json(prompt=prompt, response_schema=Dict[str, Any])
        
        if result.success:
            return result.metadata
        if reporter:
            reporter.report(f"アークの再設計に失敗しました: {result.error_message}", "error")
        return {}
""",
      "location": "in PlotAgent class"
    },
    {
      "name": "_expand_single_plot",
      "body": """
    async def _expand_single_plot(
        self,
        book_title: str,
        ep_num: int,
        arc_metadata: Dict[str, Any],
        past_context: str,
        world_settings: str,
        reporter: Optional[IReporter] = None,
        expected_ep_num: Optional[int] = None,
        system_overrides: Optional[Dict[str, Any]] = None,
    ) -> PlotEpisode:
        """単一エピソードのプロットを展開する.
        
        Args:
            book_title: 作品のタイトル
            ep_num: エピソード話数
            arc_metadata: アークメタデータ
            past_context: 過去文脈
            world_settings: 世界設定
            reporter: レポーター
            expected_ep_num: 期待話数(検証用)
            system_overrides: システムオーバーライド
            
        Returns:
            プロットエピソードモデル
            
        Raises:
            RuntimeError: プロット生成失敗時
        """
        # まず_plot_expanderを優先使用
        if hasattr(self, '_plot_expander') and self._plot_expander is not None:
            if hasattr(self._plot_expander, 'expand_single_plot'):
                try:
                    result = await self._plot_expander.expand_single_plot(
                        book_id=0,
                        ep_num=ep_num,
                        arc_metadata=arc_metadata,
                        past_context=past_context,
                        world_settings=world_settings,
                        reporter=reporter,
                        expected_ep_num=expected_ep_num,
                        system_overrides=system_overrides,
                    )
                    if result:
                        return result
                except Exception as e:
                    logger.warning(f"_plot_expanderを使用しましたが、失敗しました: {e}")

        # plot_expanderを使用できない場合は、デフォルトのプロンプトで生成
        prompt = self.pm.build_expansion_prompt(
            book_title=book_title,
            ep_num=ep_num,
            arc_metadata=arc_metadata,
            past_context=past_context,
            world_settings=world_settings,
            system_overrides=system_overrides,
        )

        result = await self.generate_json(
            prompt=prompt,
            response_schema=PlotEpisode,
            reporter=reporter,
            expected_ep_num=expected_ep_num,
        )

        if not result.success:
            raise RuntimeError(f"Episode {ep_num} プロット生成失敗: {result.error_message}")

        return PlotEpisode.model_validate(result.metadata)
""",
      "location": "in PlotAgent class"
    },
    {
      "name": "_apply_audit_loop",
      "body": """
    async def _apply_audit_loop(
        self,
        book_id: int,
        branch_id: int,
        ep_num: int,
        plot_data: PlotEpisode,
        past_context: str,
        reporter: Optional[IReporter] = None,
        max_retries: int = 3,
        system_overrides: Optional[Dict[str, Any]] = None,
    ) -> PlotEpisode:
        """監査ループを適用してプロットを生成する.
        
        Args:
            book_id: 作品ID
            branch_id: 分岐ID
            ep_num: エピソード話数
            plot_data: 生成されたプロット
            past_context: 過去文脈
            reporter: レポーター
            max_retries: 最大リトライ回数
            system_overrides: システムオーバーライド
            
        Returns:
            監査を通過したプロット
            
        Raises:
            RuntimeError: 最大リトライ超過時
        """
        last_error_summary = ""

        for attempt in range(max_retries):
            if reporter:
                reporter.update_progress(ep_num - self._start_ep_for_rebuild, 
                                        self._total_eps_for_rebuild + 1, 
                                        f"第{ep_num}話のプロット監査実行中 (試行 {attempt + 1})...")

            # ----- 論理整合性監査 -----
            audit_passed = True
            if self._auditor:
                if reporter:
                    reporter.report(f"⚖️ {ep_num}話: 監査実行中... (論理整合性チェック)", "info")

                logical_ok, logical_reason = await self._auditor.audit_logical_consistency(
                    book_id=book_id,
                    ep_num=ep_num,
                    blueprint=plot_data.detailed_blueprint,
                )

                if not logical_ok:
                    error_msg = f"論理監査失敗: {logical_reason}"
                    last_error_summary = error_msg
                    audit_passed = False
                    if reporter:
                        reporter.report(f"⚠️ {error_msg}", "warning")

            # ----- 因果律監査 -----
            if audit_passed and self._auditor and hasattr(self._auditor, 'check_integrity'):
                from src.agents.audit import PlotIntegrityMonitor
                if reporter:
                    reporter.report(f"⚖️ {ep_num}話: 監査実行中... (因果律チェック)", "info")

                try:
                    monitor = PlotIntegrityMonitor(pm=self.pm, llm=self._get_llm_client())

                    # PlotIntegrityMonitor.extract_keywords コピー
                    def extract_keywords(self, blueprint: str) -> List[str]:
                        return []

                    monitor.extract_keywords = extract_keywords.__get__(monitor, PlotIntegrityMonitor)

                    keywords = monitor.extract_keywords(plot_data.detailed_blueprint)

                    is_causal_ok, causal_score, causal_failures = await monitor.check_integrity(
                        keywords=keywords,
                        blueprint=plot_data.detailed_blueprint,
                        content=plot_data.detailed_blueprint,
                        threshold=0.7,
                    )

                    if not is_causal_ok:
                        error_msg = f"因果律監査失敗: {causal_failures}"
                        last_error_summary = error_msg
                        audit_passed = False
                        if reporter:
                            reporter.report(f"⚠️ {error_msg}", "warning")
                except Exception as e:
                    if reporter:
                        reporter.report(f"⚠️ 因果律監査エラー: {e}", "warning")

            # ----- 監査合格の場合 ----- 
            if audit_passed:
                if reporter:
                    reporter.report(f"✅ {ep_num}話: 監査合格", "success")
                return plot_data

            # ----- リトライ -----
            if attempt < max_retries - 1:
                if reporter:
                    reporter.report(f"🔄 {ep_num}話: 監査不合格、リトライ {attempt + 2}/{max_retries}", "info")

                # 修正指示付きで再生成
                retry_prompt = f"{plot_data.detailed_blueprint}\n\n\n【⚠️ 前回監査エラー(修正指示)】\n以下のエラーを解消するようにプロットを修正してください:\n{last_error_summary}"

                retry_result = await self._expand_single_plot(
                    book_title="",  # ブックタイトル取得をスキップして簡略化
                    ep_num=ep_num,
                    arc_metadata={},  # 既存 arc_metadata を使用したい場合は保持
                    past_context=f"{past_context}\n\n修正前の監査エラー:\n{last_error_summary}",
                    world_settings="",
                    reporter=reporter,
                    system_overrides=system_overrides,
                )

                if retry_result:
                    plot_data = retry_result
                    continue

        # ----- 最大リトライ超過 ----- 
        raise RuntimeError(f"{ep_num}話: 監査リトライ最大回数({max_retries})を超過。最終エラー: {last_error_summary}")
""",
      "location": "in PlotAgent class"
    },
    {
      "name": "_archive_and_save_plots",
      "body": """
    async def _archive_and_save_plots(
        self,
        book_id: int,
        branch_id: int,
        start_ep: int,
        new_total: int,
        new_plots: List[PlotEpisode],
        reporter: Optional[IReporter] = None,
    ) -> List[PlotEpisode]:
        """古いプロットをアーカイブし、新しいプロットを保存する.
        
        Args:
            book_id: 作品ID
            branch_id: 分岐ID
            start_ep: 再構築開始話数
            new_total: 新しい総話数
            new_plots: 保存するプロットリスト
            reporter: レポーター
            
        Returns:
            保存されたプロットリスト
        """
        if not new_plots:
            return []

        try:
            async with self._uow():
                if reporter:
                    reporter.report(f"💾 データベースを更新中... (第{start_ep}話以降のアーカイブ/保存)", "info")

                # 古いプロットを削除
                if hasattr(self.repo, 'archive_plots_from'):
                    await self.repo.archive_plots_from(branch_id, start_ep, new_total)
                else:
                    # 代替メソッド: delete_plots_from
                    await self.repo.delete_plots_from(branch_id, start_ep)

                # 新しいプロットを保存
                saved_plots = []
                for plot in new_plots:
                    await self.repo.save_plot(branch_id, plot.ep_num, plot)
                    saved_plots.append(plot)

                if reporter:
                    reporter.report(f"✅ プロットの保存完了: {len(saved_plots)}話を保存", "success")

            return saved_plots

        except Exception as e:
            logger.error(f"データベース保存エラー: {e}")
            if reporter:
                reporter.report(f"🚨 データベース保存エラー: {e}", "error")
            return []
""",
      "location": "in PlotAgent class"
    }
  ]
}
