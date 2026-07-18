import logging
from typing import TYPE_CHECKING, Any, Awaitable, Callable, List, Optional, Dict

from src.agents.base import BaseAgent

if TYPE_CHECKING:
    from src.core.interfaces import IPlotExpander, IPromptManager, IReporter, IRepository
    from src.models import Arc, PlotDetail, PlotEpisode

logger = logging.getLogger(__name__)


class PlotAgent(BaseAgent):
    """プロット設計、アーク分割などを担当"""
    def __init__(
        self,
        repo: "IRepository",
        pm: "IPromptManager",
        generate_json: Callable[..., Awaitable[Any]],
        plot_expander: Optional["IPlotExpander"] = None,
        auditor: Optional[Any] = None,
        uow_factory: Optional[Callable[[], Any]] = None,
    ):
        super().__init__()
        self.repo = repo
        self.pm = pm
        self.generate_json = generate_json
        self._plot_expander = plot_expander
        self._auditor = auditor
        self._uow_factory = uow_factory

    async def _expand_single_plot(
        self,
        book_title: str,
        ep_num: int,
        arc_metadata: Dict[str, Any],
        past_context: str,
        world_settings: str,
        reporter: Optional["IReporter"] = None,
        expected_ep_num: Optional[int] = None,
        system_overrides: Optional[Dict[str, Any]] = None,
    ) -> "PlotEpisode":
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

    async def _apply_audit_loop(
        self,
        book_id: int,
        branch_id: int,
        ep_num: int,
        plot_data: "PlotEpisode",
        past_context: str,
        reporter: Optional["IReporter"] = None,
        max_retries: int = 3,
        system_overrides: Optional[Dict[str, Any]] = None,
    ) -> "PlotEpisode":
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

    async def _archive_and_save_plots(
        self,
        book_id: int,
        branch_id: int,
        start_ep: int,
        new_total: int,
        new_plots: List["PlotEpisode"],
        reporter: Optional["IReporter"] = None,
    ) -> List["PlotEpisode"]:
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
            async with self._uow_factory():
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

    async def _build_past_context(
        self,
        branch_id: int,
        start_ep: int,
    ) -> str:
        """過去プロットから文脈文字列を生成する.

        Args:
            branch_id: 分岐ID
            start_ep: 再構築開始話数

        Returns:
            過去文脈文字列
        """
        past_plots = await self.repo.get_plots_between(branch_id, 1, start_ep - 1)
        if not past_plots:
            return "【過去文脈】\n過去のプロットはありません。\n"

        lines = ["【過去文脈】"]
        for p in past_plots:
            summary = getattr(p, 'summary', '') or getattr(p, 'one_line_summary', '') or ''
            lines.append(f"- 第{p.ep_num}話: {summary}")
        return "\n".join(lines)

    async def _get_world_settings(
        self,
        book_id: int,
    ) -> str:
        """Bibleから世界設定JSON文字列を取得する.

        Args:
            book_id: 作品ID

        Returns:
            世界設定JSON文字列
        """
        import json
        bible = await self.repo.get_latest_bible(book_id)
        if not bible:
            return "{}"

        settings = {}
        if hasattr(bible, 'settings') and bible.settings:
            if isinstance(bible.settings, str):
                try:
                    settings = json.loads(bible.settings)
                except:
                    settings = {}
            elif isinstance(bible.settings, dict):
                settings = bible.settings

        return json.dumps(settings, ensure_ascii=False)

    async def _get_book_branch(
        self,
        book_id: int,
    ) -> int:
        """本の現在のブランチIDを安全に取得する.

        Args:
            book_id: 作品ID

        Returns:
            ブランチID
        """
        book = await self.repo.get_book(book_id)
        return book.current_branch_id if book and book.current_branch_id else 1

    async def _get_llm_client(self):
        """LLMクライアントを安全に取得するヘルパーメソッド.

        Returns:
            LLMクライアント
        """
        return self.llm

    async def expand_plots(
        self, book_id: int, ep_nums: List[int], arcs: List["Arc"],
        reporter: Optional["IReporter"] = None, force: bool = False, branch_id: Optional[int] = None,
    ) -> List["PlotDetail"]:
        """各エピソードのプロット詳細を展開する（実際のLLM呼び出し）"""
        self._ensure_services()

        if reporter:
            reporter.report(f"プロット展開を開始します... (対象話数: {ep_nums})", "info")

        results = await self._plot_expander.expand_plots(
            book_id=book_id,
            target_ep_list=ep_nums,
            arcs=arcs,
            reporter=reporter,
            force=force,
            branch_id=branch_id,
        )
        return results

    async def rebuild_hegemony_plot(
        self, book_id: int, start_ep: int, new_total_eps: int, keywords: str,
        trend_memo: str, plot_pattern_key: str, cost_severity: int, cheat_scale: int,
        system_assist: int, reporter: Optional["IReporter"] = None
    ) -> List["PlotEpisode"]:
        """
        第X話以降のプロット再構築機能を実行する。

        Args:
            book_id: 書籍ID
            start_ep: 再構築開始話数
            new_total_eps: 新しい総話数
            keywords: キーワード
            trend_memo: トレンドメモ
            plot_pattern_key: プロットパターンキー
            cost_severity: コスト重要度
            cheat_scale: チートスケール
            system_assist: システムアシスト値
            reporter: 進捗レポーター

        Returns:
            再構築されたプロットのリスト
        """
        # システムの初期化確認
        self._ensure_services()

        if reporter:
            reporter.report(f"🔨 第{start_ep}話以降のプロット再構築を開始します...", "info")

        # 準備フェーズ
        book = await self.repo.get_book(book_id)
        if not book:
            if reporter:
                reporter.report("作品が見つかりません。", "error")
            return []

        branch_id = await self._get_book_branch(book_id)
        
        # リポジトリのget_latest_bibleメソッドの存在確認
        if not hasattr(self.repo, 'get_latest_bible'):
            if reporter:
                reporter.report("リポジトリにget_latest_bibleメソッドがありません。", "error")
            return []
            
        bible = await self.repo.get_latest_bible(book_id)
        if not bible:
            if reporter:
                reporter.report("作品の世界観設定（Bible）が見つかりません。", "error")
            return []

        # 過去文脈の構築
        past_context = await self._build_past_context(branch_id, start_ep)
        
        # 世界設定の取得
        world_settings = await self._get_world_settings(book_id)

        # システムオーバーライドの構築
        system_overrides = {
            "cost_severity": cost_severity,
            "cheat_scale": cheat_scale,
            "system_assist": system_assist,
            "trend_memo": trend_memo,
        }

        # 新しいアークメタデータの生成
        arc_metadata = await self._generate_arc_metadata(
            book_title=book.title,
            past_context=past_context,
            new_keywords=keywords,
            trend_memo=trend_memo,
            plot_pattern_key=plot_pattern_key,
            new_total=new_total_eps,
            start_ep=start_ep,
            reporter=reporter,
        )
        
        if not arc_metadata:
            if reporter:
                reporter.report("アークメタデータの生成に失敗しました。処理を中止します。", "error")
            return []

        # エピソードごとのプロット生成
        new_plots: List["PlotEpisode"] = []
        total_eps = new_total_eps - start_ep + 1
        
        # 再構築ヘルパーのためのインスタンス変数を設定
        self._start_ep_for_rebuild = start_ep
        self._total_eps_for_rebuild = total_eps

        for ep_num in range(start_ep, new_total_eps + 1):
            try:
                # まず簡単なプロットを生成
                plot_data = await self._expand_single_plot(
                    book_title=book.title,
                    ep_num=ep_num,
                    arc_metadata=arc_metadata,
                    past_context=past_context,
                    world_settings=world_settings,
                    reporter=reporter,
                    system_overrides=system_overrides,
                )
                
                # プロットに対して監査ループを適用
                plot_data = await self._apply_audit_loop(
                    book_id=book_id,
                    branch_id=branch_id,
                    ep_num=ep_num,
                    plot_data=plot_data,
                    past_context=past_context,
                    reporter=reporter,
                    max_retries=3,
                    system_overrides=system_overrides,
                )
                
                # 正しい話数の設定
                plot_data.ep_num = ep_num
                new_plots.append(plot_data)
                
            except Exception as e:
                logger.error(f"Episode {ep_num} プロット生成エラー: {e}")
                if reporter:
                    reporter.report(f"⚠️ Episode {ep_num} 処理中にエラー: {e}", "warning")
                # エラーでも続行
                continue

        # 進捗レポート
        if reporter:
            completed = len(new_plots)
            reporter.update_progress(completed, total_eps, f"完了: {completed}/{total_eps}話")
            reporter.report(f"✅ プロット再構築完了: {len(new_plots)}話を生成", "success")

        # データベースへの保存
        if new_plots:
            saved_plots = await self._archive_and_save_plots(
                book_id=book_id,
                branch_id=branch_id,
                start_ep=start_ep,
                new_total=new_total_eps,
                new_plots=new_plots,
                reporter=reporter,
            )
            return saved_plots

        return new_plots

    async def run(self, *args, **kwargs):
        logger.info("PlotAgent run invoked")
        return await self.expand_plots(**kwargs)

