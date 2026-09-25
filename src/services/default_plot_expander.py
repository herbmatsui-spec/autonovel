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
from typing import Any

from config.constants import MODEL_PLOT_EXPANSION, MODEL_PLANNING, MODEL_FAST_EXPANSION
from src.core.interfaces import IReporter, IRepository
from src.models.plot import (
    UltraFastPlotBatch,
    EpisodeMacroSkeleton,
    PlotMacroBatch,
    PlotMicroBlueprint,
    merge_macro_and_micro,
    PlotEpisode,
)

logger = logging.getLogger(__name__)


class DefaultPlotExpander:
    """IPlotExpander の標準実装。

    大局骨子の一括生成(Macro)と執筆直前の詳細ビートJIT展開(Micro)をサポートする。
    """

    def __init__(self, repo: IRepository, pm: Any, llm: Any):
        self.repo = repo
        self.pm = pm
        self.llm = llm
        self.model_planning = MODEL_PLANNING
        self.model_fast = MODEL_FAST_EXPANSION

    async def expand_macro_skeletons(
        self,
        book_id: int,
        target_ep_list: list[int],
        reporter: IReporter | None = None,
        branch_id: int | None = None,
    ) -> list[EpisodeMacroSkeleton]:
        """大局骨子(Macro Skeleton)を一括バッチ生成してDBに保存する"""
        if not target_ep_list:
            return []

        if reporter:
            reporter.report(f"大局プロット骨子の一括生成を開始: 対象={target_ep_list}", "info")

        try:
            bible = await self.repo.get_latest_bible(book_id)
        except Exception as e:
            logger.error(f"Failed to fetch bible for book_id={book_id}: {e}")
            return []

        if bible is None:
            logger.warning(f"No bible found for book_id={book_id}, cannot expand macro skeletons")
            return []

        bible_dict = (
            bible.model_dump()
            if hasattr(bible, "model_dump")
            else (bible if isinstance(bible, dict) else {})
        )
        bible_json_str = json.dumps(bible_dict, ensure_ascii=False)

        prompt = await self.pm.build_macro_plot_skeleton_prompt(
            bible_json_str, target_ep_list, book_id=book_id
        )

        res = await self.llm.generate_json(
            self.model_planning,
            prompt,
            response_schema=PlotMacroBatch,
            reporter=reporter,
        )

        if isinstance(res, PlotMacroBatch):
            batch = res
        else:
            metadata = getattr(res, "metadata", None) or (res if isinstance(res, dict) else {})
            if hasattr(metadata, "model_dump"):
                metadata = metadata.model_dump()
            batch = PlotMacroBatch.model_validate(metadata)

        skeletons = batch.episodes
        for sk in skeletons:
            existing = await self.repo.get_plot(book_id, sk.ep_num, branch_id=branch_id)
            if existing is None:
                dummy_micro = PlotMicroBlueprint(ep_num=sk.ep_num)
                partial_plot = merge_macro_and_micro(sk, dummy_micro)
                await self.repo.save_plot(book_id, sk.ep_num, partial_plot)

        if reporter:
            reporter.report(f"大局プロット骨子生成完了: {len(skeletons)}話分", "info")

        return skeletons

    async def expand_single_micro(
        self,
        book_id: int,
        ep_num: int,
        skeleton: EpisodeMacroSkeleton,
        previous_ending_text: str = "",
        reporter: IReporter | None = None,
        branch_id: int | None = None,
    ) -> PlotEpisode:
        """単一話の詳細演出ビートをJIT展開して合成する"""
        if reporter:
            reporter.report(f"第{ep_num}話: 詳細演出ビートを展開中...", "info")

        chars_summary = ""
        try:
            chars = await self.repo.get_characters(book_id)
            if chars:
                char_lines = []
                for c in chars:
                    name = getattr(c, "name", "")
                    flaw = getattr(c, "secret_flaw", "") or getattr(c, "personality", "")
                    char_lines.append(f"- {name}: {flaw}")
                chars_summary = "\n".join(char_lines)
        except Exception as e:
            logger.debug(f"Failed to fetch characters for micro expansion: {e}")

        prompt = await self.pm.build_micro_scene_expander_prompt(
            macro_skeleton=skeleton,
            previous_ending_text=previous_ending_text[-500:].strip() if previous_ending_text else "",
            characters_summary=chars_summary,
            book_id=book_id,
        )

        res = await self.llm.generate_json(
            self.model_fast,
            prompt,
            response_schema=PlotMicroBlueprint,
            reporter=reporter,
        )

        if isinstance(res, PlotMicroBlueprint):
            micro_bp = res
        else:
            metadata = getattr(res, "metadata", None) or (res if isinstance(res, dict) else {})
            if hasattr(metadata, "model_dump"):
                metadata = metadata.model_dump()
            micro_bp = PlotMicroBlueprint.model_validate(metadata)

        merged_plot = merge_macro_and_micro(skeleton, micro_bp)
        await self.repo.save_plot(book_id, ep_num, merged_plot)

        if reporter:
            reporter.report(f"第{ep_num}話: 詳細演出ビート展開完了", "info")

        return merged_plot

    async def ensure_detailed_plot(
        self,
        book_id: int,
        ep_num: int,
        branch_id: int = 1,
        reporter: IReporter | None = None,
    ) -> PlotEpisode:
        """指定話数の詳細プロットが存在することを保証する（完全冪等）"""
        existing = await self.repo.get_plot(book_id, ep_num, branch_id=branch_id)
        if existing and hasattr(existing, "scenes") and len(existing.scenes) >= 3:
            return existing

        skeleton: EpisodeMacroSkeleton
        if existing and hasattr(existing, "extract_macro_skeleton"):
            skeleton = existing.extract_macro_skeleton()
        else:
            skeletons = await self.expand_macro_skeletons(
                book_id, [ep_num], reporter=reporter, branch_id=branch_id
            )
            skeleton = skeletons[0] if skeletons else EpisodeMacroSkeleton(ep_num=ep_num)

        prev_ending_text = ""
        if ep_num > 1:
            try:
                prev_ch = await self.repo.get_chapter(book_id, branch_id, ep_num - 1)
                if prev_ch and hasattr(prev_ch, "content") and prev_ch.content:
                    prev_ending_text = prev_ch.content
            except Exception as e:
                logger.debug(f"Failed to fetch prev chapter for Ep.{ep_num}: {e}")

        return await self.expand_single_micro(
            book_id=book_id,
            ep_num=ep_num,
            skeleton=skeleton,
            previous_ending_text=prev_ending_text,
            reporter=reporter,
            branch_id=branch_id,
        )

    def prefetch_next_episode_plot(
        self,
        book_id: int,
        next_ep: int,
        branch_id: int = 1,
    ) -> asyncio.Task | None:
        """次話の詳細プロットを非同期バックグラウンドで先行展開する（レイテンシ隠蔽）"""
        async def _prefetch():
            try:
                await self.ensure_detailed_plot(book_id, next_ep, branch_id=branch_id)
            except Exception as e:
                logger.debug(f"Prefetch failed for Ep.{next_ep} (non-blocking): {e}")

        return asyncio.create_task(_prefetch())

    async def expand_plots(
        self,
        book_id: int,
        target_ep_list: list[int],
        arcs: list[Any],
        reporter: IReporter | None = None,
        force: bool = False,
        branch_id: int | None = None,
    ) -> list[Any]:
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

        results: list[Any] = []
        sem = asyncio.Semaphore(2)

        async def _process_single(ep_num: int) -> Any | None:
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
