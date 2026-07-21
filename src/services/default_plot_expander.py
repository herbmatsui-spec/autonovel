"""
src/services/default_plot_expander.py — デフォルトのプロット展開実装

IPlotExpander プロトコルの標準実装。
bible_service.py の超高速プロット生成ロジックを再利用し、
PlotAgent から独立して呼び出せるようにする。
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, List, Optional

from config.constants import MODEL_PLOT_EXPANSION
from src.core.interfaces import IPlotExpander, IReporter, IRepository
from src.models.plot import UltraFastPlotBatch

logger = logging.getLogger(__name__)


class DefaultPlotExpander:
    """IPlotExpander の標準実装。

    バイブル情報を元に、指定されたエピソード群の詳細プロットを
    一括生成して DB に保存する。
    """

    def __init__(self, repo: IRepository, pm: Any, llm: Any):
        self.repo = repo
        self.pm = pm
        self.llm = llm

    async def expand_plots(
        self,
        book_id: int,
        target_ep_list: List[int],
        arcs: List[Any],
        reporter: Optional[IReporter] = None,
        force: bool = False,
        branch_id: Optional[int] = None,
    ) -> List[Any]:
        """各エピソードのプロット詳細を展開する。"""
        if not target_ep_list:
            return []

        if reporter:
            reporter.report(f"プロット展開を開始: 対象={target_ep_list}", "info")

        try:
            bible = await self.repo.get_latest_bible(book_id)
        except Exception as e:
            logger.error(f"Failed to fetch bible for book_id={book_id}: {e}")
            return []

        if bible is None:
            logger.warning(f"No bible found for book_id={book_id}, cannot expand plots")
            return []

        bible_dict = {}
        if hasattr(bible, "model_dump"):
            bible_dict = bible.model_dump()
        elif isinstance(bible, dict):
            bible_dict = bible
        else:
            logger.warning(f"Unexpected bible type: {type(bible)}")
            return []

        if arcs:
            bible_dict["arcs"] = arcs

        bible_json_str = json.dumps(bible_dict, ensure_ascii=False)

        results: List[Any] = []
        sem = asyncio.Semaphore(2)

        async def _process_single(ep_num: int) -> Optional[Any]:
            async with sem:
                try:
                    existing = await self.repo.get_plot(book_id, ep_num, branch_id=branch_id)
                    if existing and not force:
                        if (
                            hasattr(existing, "detailed_blueprint")
                            and existing.detailed_blueprint
                            and len(existing.detailed_blueprint) > 50
                        ):
                            if reporter:
                                reporter.report(f"Ep.{ep_num}: 既存プロットを再利用", "debug")
                            return existing

                    plot_prompt = await self.pm.build_ultra_fast_plot_batch_prompt(
                        bible_json_str, [ep_num], book_id=book_id
                    )
                    plot_res = await self.llm.generate_json(
                        MODEL_PLOT_EXPANSION,
                        plot_prompt,
                        response_schema=UltraFastPlotBatch,
                        reporter=reporter,
                    )
                    if not plot_res.success:
                        logger.error(
                            f"Plot generation failed for Ep.{ep_num}: {plot_res.error_message}"
                        )
                        return None

                    plots = UltraFastPlotBatch.model_validate(plot_res.metadata).plots
                    if not plots:
                        logger.warning(f"No plots returned for Ep.{ep_num}")
                        return None

                    plot = plots[0]
                    await self.repo.save_plot(book_id, ep_num, plot)
                    if reporter:
                        reporter.report(f"Ep.{ep_num}: プロット生成完了", "info")
                    return plot
                except Exception as e:
                    logger.error(f"Plot generation error for Ep.{ep_num}: {e}")
                    return None

        tasks = [asyncio.create_task(_process_single(ep)) for ep in target_ep_list]
        done = await asyncio.gather(*tasks, return_exceptions=True)

        for item in done:
            if isinstance(item, Exception):
                logger.error(f"Plot generation task failed: {item}")
            elif item is not None:
                results.append(item)

        if reporter:
            reporter.report(f"プロット展開完了: {len(results)}/{len(target_ep_list)}話", "info")

        return results
