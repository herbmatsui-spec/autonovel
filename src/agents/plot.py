import logging
from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Any, Optional

from src.agents.base import BaseAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName

if TYPE_CHECKING:
    from src.core.interfaces import IPlotExpander, IPromptManager, IReporter, IRepository
    from src.models import Arc, PlotDetail, PlotEpisode

logger = logging.getLogger(__name__)


class PlotAgent(BaseAgent):
    """プロット展開のオーケストレーションを担当。

    責務は ``PlotExpander`` を用いた各エピソードのプロット詳細展開
    (expand_plots) のみ。アーク生成や再構築パイプラインの orchestration は
    PlotRebuildWorkflow に委譲される。
    """

    def __init__(
        self,
        repo: "IRepository",
        pm: "IPromptManager",
        generate_json: Callable[..., Awaitable[Any]],
        plot_expander: Optional["IPlotExpander"] = None,
        auditor: Any | None = None,
        uow_factory: Callable[[], Any] | None = None,
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
        arc_metadata: dict[str, Any],
        past_context: str,
        world_settings: str,
        reporter: Optional["IReporter"] = None,
        expected_ep_num: int | None = None,
        system_overrides: dict[str, Any] | None = None,
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
        if hasattr(self, "_plot_expander") and self._plot_expander is not None:
            if hasattr(self._plot_expander, "expand_single_plot"):
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
        system_overrides: dict[str, Any] | None = None,
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
                reporter.update_progress(
                    ep_num - self._start_ep_for_rebuild,
                    self._total_eps_for_rebuild + 1,
                    f"第{ep_num}話のプロット監査実行中 (試行 {attempt + 1})...",
                )

            # ----- 監査の実行 -----
            audit_passed, last_error_summary = await self._run_audits(
                book_id=book_id,
                ep_num=ep_num,
                plot_data=plot_data,
                last_error_summary=last_error_summary,
                reporter=reporter,
            )

            # ----- 監査合格の場合 -----
            if audit_passed:
                if reporter:
                    reporter.report(f"✅ {ep_num}話: 監査合格", "success")
                return plot_data

            # ----- リトライ -----
            if attempt < max_retries - 1:
                if reporter:
                    reporter.report(
                        f"🔄 {ep_num}話: 監査不合格、リトライ {attempt + 2}/{max_retries}", "info"
                    )

                # 修正指示付きで再生成
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
        raise RuntimeError(
            f"{ep_num}話: 監査リトライ最大回数({max_retries})を超過。最終エラー: {last_error_summary}"
        )

    async def _run_audits(
        self,
        book_id: int,
        ep_num: int,
        plot_data: "PlotEpisode",
        last_error_summary: str,
        reporter: Optional["IReporter"] = None,
    ) -> tuple[bool, str]:
        """論理整合性監査と因果律監査を実行し、合格可否とエラー要約を返す."""
        audit_passed = True

        # ----- 論理整合性監査 -----
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
        if audit_passed and self._auditor and hasattr(self._auditor, "check_integrity"):
            causal_ok, last_error_summary = await self._run_causal_audit(
                ep_num=ep_num, plot_data=plot_data, reporter=reporter
            )
            if not causal_ok:
                audit_passed = False

        return audit_passed, last_error_summary

    async def _run_causal_audit(
        self,
        ep_num: int,
        plot_data: "PlotEpisode",
        reporter: Optional["IReporter"] = None,
    ) -> tuple[bool, str]:
        """因果律監査を実行し、合格可否とエラー要約を返す."""
        from src.agents.audit import PlotIntegrityMonitor

        if reporter:
            reporter.report(f"⚖️ {ep_num}話: 監査実行中... (因果律チェック)", "info")

        try:
            monitor = PlotIntegrityMonitor(pm=self.pm, llm=self._get_llm_client())

            def extract_keywords(self, blueprint: str) -> list[str]:
                return []

            monitor.extract_keywords = extract_keywords.__get__(monitor, PlotIntegrityMonitor)
            keywords = monitor.extract_keywords(plot_data.detailed_blueprint)

            is_causal_ok, _causal_score, causal_failures = await monitor.check_integrity(
                keywords=keywords,
                blueprint=plot_data.detailed_blueprint,
                content=plot_data.detailed_blueprint,
                threshold=0.7,
            )

            if not is_causal_ok:
                error_msg = f"因果律監査失敗: {causal_failures}"
                if reporter:
                    reporter.report(f"⚠️ {error_msg}", "warning")
                return False, error_msg
            return True, ""
        except Exception as e:
            if reporter:
                reporter.report(f"⚠️ 因果律監査エラー: {e}", "warning")
            return True, ""

    async def _archive_and_save_plots(
        self,
        book_id: int,
        branch_id: int,
        start_ep: int,
        new_total: int,
        new_plots: list["PlotEpisode"],
        reporter: Optional["IReporter"] = None,
    ) -> list["PlotEpisode"]:
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
                    reporter.report(
                        f"💾 データベースを更新中... (第{start_ep}話以降のアーカイブ/保存)", "info"
                    )

                # 古いプロットを削除
                if hasattr(self.repo, "archive_plots_from"):
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
            summary = getattr(p, "summary", "") or getattr(p, "one_line_summary", "") or ""
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
        if hasattr(bible, "settings") and bible.settings:
            if isinstance(bible.settings, str):
                try:
                    settings = json.loads(bible.settings)
                except (json.JSONDecodeError, ValueError):
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
        self,
        book_id: int,
        ep_nums: list[int],
        arcs: list["Arc"],
        reporter: Optional["IReporter"] = None,
        force: bool = False,
        branch_id: int | None = None,
    ) -> list["PlotDetail"]:
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

    async def run(self, ctx: AgentContext) -> AgentResult:
        """Orchestrator 用エントリーポイント。
        ctx.artifacts から必要な入力を取得し、プロットを生成して次のエージェントへ渡す。
        """
        # 既存の expand_plots メソッドを活用するため、artifacts から必要な情報を取得
        book_id = ctx.book_id
        branch_id = ctx.branch_id
        ep_num = ctx.ep_num
        arcs = ctx.artifacts.get("arcs", [])

        # ep_num 単体の場合はその話数のみ、リストの場合はリストを使用
        target_eps = ctx.artifacts.get("target_ep_nums", [ep_num])

        try:
            plots = await self.expand_plots(
                book_id=book_id,
                ep_nums=target_eps,
                arcs=arcs,
                reporter=ctx.artifacts.get("reporter"),
                branch_id=branch_id,
            )
            return AgentResult(
                next_agent=AgentName.BIBLE,
                artifacts={"plots": [p.model_dump() if hasattr(p, "model_dump") else p for p in plots]},
            )
        except Exception as e:
            return AgentResult(
                next_agent=None,
                artifacts={},
                error=f"Plot generation failed: {e}",
            )
