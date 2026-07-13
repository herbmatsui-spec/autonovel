from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from src.agents.writing import WritingAgent

logger = logging.getLogger(__name__)

class PipelineContext(BaseModel):
    book_id: int
    branch_id: int
    start_ep: int
    end_ep: int
    passion: float = 0.5
    target_word_count: int = 2000
    is_easy_mode: bool = False
    style_tag: Optional[str] = None
    total_chars: int = 0
    failed_episodes: List[Dict[str, Any]] = Field(default_factory=list)
    written_count: int = 0
    total_to_write: int = 0
    bible: Optional[Any] = None
    settings: Dict[str, Any] = Field(default_factory=dict)
    scheduler: Optional[Any] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude={"bible", "scheduler"})

class PipelineStep:
    async def execute(self, ep_num: int, ctx: PipelineContext, agent: WritingAgent, reporter: Any) -> bool:
        """Execute step. Returns True to continue, False to halt/break."""
        raise NotImplementedError()

class PlotReadyStep(PipelineStep):
    async def execute(self, ep_num: int, ctx: PipelineContext, agent: WritingAgent, reporter: Any) -> bool:
        if ctx.scheduler is None:
            return False
        try:
            plot = await ctx.scheduler.await_plot_ready(ep_num)
            # We temporarily store the plot in the context or pass it along,
            # but since it's saved in DB/scheduler, we can fetch it when needed.
            return True
        except Exception as e:
            ctx.failed_episodes.append({"ep_num": ep_num, "error_message": str(e)})
            if reporter:
                reporter.report(f"❌ 第{ep_num}話 プロット待機エラー: {e}", "error")
            return False

class PrefetchStep(PipelineStep):
    async def execute(self, ep_num: int, ctx: PipelineContext, agent: WritingAgent, reporter: Any) -> bool:
        if agent.style_rag and agent.rag_prefetch:
            try:
                plot = await agent.repo.get_plot(ctx.branch_id, ep_num)
                if plot:
                    await agent.rag_prefetch.prefetch_for_episode(
                        engine=agent.llm,
                        book_id=ctx.book_id,
                        branch_id=ctx.branch_id,
                        ep_num=ep_num,
                        plot_blueprint=plot.detailed_blueprint or plot.summary or ""
                    )
            except Exception as e:
                logger.warning(f"RAG prefetch failed for Ep.{ep_num}: {e}")
        return True

class ApplyPatchStep(PipelineStep):
    async def execute(self, ep_num: int, ctx: PipelineContext, agent: WritingAgent, reporter: Any) -> bool:
        if ep_num > 1:
            try:
                prev_ch = await agent.repo.get_chapter(ctx.branch_id, ep_num - 1)
                if prev_ch and prev_ch.ai_insight:
                    insight_text = prev_ch.ai_insight.strip()
                    if insight_text:
                        plot = await agent.repo.get_plot(ctx.branch_id, ep_num)
                        if plot:
                            patched_blueprint = f"【前話からの確定事実（パッチ）】\n{insight_text}\n\n{plot.detailed_blueprint}"
                            await agent.repo.update_plot_blueprint(ctx.branch_id, ep_num, patched_blueprint)
                            if reporter:
                                reporter.report(f"🔧 第{ep_num}話: 前話の確定事実をプロットにパッチ当てしました。", "info")
            except Exception as e:
                logger.error(f"Failed to apply patch for Ep.{ep_num}: {e}")
        return True

class DraftingStep(PipelineStep):
    async def execute(self, ep_num: int, ctx: PipelineContext, agent: WritingAgent, reporter: Any) -> bool:
        try:
            if reporter:
                reporter.report(f"✍️ 第{ep_num}話の本編を執筆中...", "info")
            count = await agent.generate_episodes(
                ctx.book_id, ep_num, ep_num, ctx.passion, ctx.target_word_count,
                False, reporter, ctx.is_easy_mode, branch_id=ctx.branch_id, style_tag=ctx.style_tag
            )
            if count == 0:
                raise RuntimeError(f"第{ep_num}話の本文生成結果が空（0文字）です。")
            ctx.total_chars += count
            ctx.written_count += 1

            # --- Bible Agent Extraction Trigger ---
            try:
                # agent.generate_episodes uses a GenerationLoopManager which returns final_content.
                # However, DraftingStep calls agent.generate_episodes.
                # We need the actual content. Since agent.generate_episodes only returns count,
                # we must modify WritingAgent to provide the content or fetch it from DB.
                last_ch = await agent.repo.get_chapter(ctx.branch_id, ep_num)
                if last_ch and last_ch.content:
                    await agent.trigger_bible_extraction(ctx.book_id, last_ch.content, reporter)
            except Exception as ex:
                logger.warning(f"Bible extraction trigger failed for Ep.{ep_num}: {ex}")

            if reporter:
                reporter.update_progress(
                    ctx.written_count, ctx.total_to_write,
                    f"🚀 執筆パイプライン ({ctx.written_count}/{ctx.total_to_write}話)",
                    f"第{ep_num}話の執筆が完了しました。 ({count}文字)"
                )
            return True
        except Exception as e:
            logger.error(f"Writing failed for Ep.{ep_num}: {e}", exc_info=True)
            ctx.failed_episodes.append({"ep_num": ep_num, "error_message": str(e)})
            if reporter:
                reporter.report(f"❌ 第{ep_num}話 執筆エラー: {e}。パイプライン処理を緊急停止しました。", "error")
            raise e

class WritingPipeline:
    def __init__(self, steps: List[PipelineStep]):
        self.steps = steps

    async def execute(self, ctx: PipelineContext, agent: WritingAgent, reporter: Any) -> Tuple[int, List[Dict[str, Any]]]:
        book = await agent.repo.get_book(ctx.book_id)
        if ctx.branch_id is None:
            ctx.branch_id = book.current_branch_id if book and book.current_branch_id else 1

        ctx.total_to_write = ctx.end_ep - ctx.start_ep + 1
        ctx.written_count = 0

        bible = await agent.repo.get_latest_bible(ctx.book_id)
        settings = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings or "{}") if bible else {}
        arcs = settings.get("arcs") or getattr(bible, "arcs", []) if bible else []
        ctx.bible = bible
        ctx.settings = settings

        from src.agents.writing_scheduler import StreamingPlotScheduler
        scheduler = StreamingPlotScheduler(agent.repo, agent.llm, agent.pm, agent.planner, ctx.book_id, ctx.branch_id, arcs, ctx.end_ep, reporter)
        await scheduler.schedule_plot_generation(ctx.start_ep, bible, settings)
        ctx.scheduler = scheduler

        for ep_num in range(ctx.start_ep, ctx.end_ep + 1):
            if reporter and reporter.state.should_stop():
                break
            await scheduler.schedule_plot_generation(ep_num + 1, bible, settings)

            # 進捗再開用のコンテキストをDBに保存
            if reporter and hasattr(reporter, "state"):
                state_dict = ctx.to_dict()
                state_dict["current_ep_num"] = ep_num
                reporter.state.result_data = {"pipeline_type": "writing", "context": state_dict}
                reporter.state._save_to_db()

            for step in self.steps:
                try:
                    success = await step.execute(ep_num, ctx, agent, reporter)
                except Exception as e:
                    # 失敗時もその時点のコンテキストを保存
                    if reporter and hasattr(reporter, "state"):
                        state_dict = ctx.to_dict()
                        state_dict["current_ep_num"] = ep_num
                        reporter.state.result_data = {"pipeline_type": "writing", "context": state_dict}
                        reporter.state._save_to_db()
                    raise e

                if not success:
                    # 失敗時もその時点のコンテキストを保存
                    if reporter and hasattr(reporter, "state"):
                        state_dict = ctx.to_dict()
                        state_dict["current_ep_num"] = ep_num
                        reporter.state.result_data = {"pipeline_type": "writing", "context": state_dict}
                        reporter.state._save_to_db()
                    return ctx.total_chars, ctx.failed_episodes

        return ctx.total_chars, ctx.failed_episodes

    async def resume(self, ctx_data: Dict[str, Any], agent: WritingAgent, reporter: Any) -> Tuple[int, List[Dict[str, Any]]]:
        """失敗したエピソード番号からパイプラインを再開します"""
        current_ep_num = ctx_data.pop("current_ep_num", ctx_data["start_ep"])
        ctx = PipelineContext(**ctx_data)

        book = await agent.repo.get_book(ctx.book_id)
        if ctx.branch_id is None:
            ctx.branch_id = book.current_branch_id if book and book.current_branch_id else 1

        bible = await agent.repo.get_latest_bible(ctx.book_id)
        settings = bible.settings if isinstance(bible.settings, dict) else json.loads(bible.settings or "{}") if bible else {}
        arcs = settings.get("arcs") or getattr(bible, "arcs", []) if bible else []
        ctx.bible = bible
        ctx.settings = settings

        from src.agents.writing_scheduler import StreamingPlotScheduler
        scheduler = StreamingPlotScheduler(agent.repo, agent.llm, agent.pm, agent.planner, ctx.book_id, ctx.branch_id, arcs, ctx.end_ep, reporter)
        await scheduler.schedule_plot_generation(current_ep_num, bible, settings)
        ctx.scheduler = scheduler

        # 未完了のエピソード（current_ep_num）からループを開始
        for ep_num in range(current_ep_num, ctx.end_ep + 1):
            if reporter and reporter.state.should_stop():
                break
            await scheduler.schedule_plot_generation(ep_num + 1, bible, settings)

            if reporter and hasattr(reporter, "state"):
                state_dict = ctx.to_dict()
                state_dict["current_ep_num"] = ep_num
                reporter.state.result_data = {"pipeline_type": "writing", "context": state_dict}
                reporter.state._save_to_db()

            for step in self.steps:
                success = await step.execute(ep_num, ctx, agent, reporter)
                if not success:
                    if reporter and hasattr(reporter, "state"):
                        state_dict = ctx.to_dict()
                        state_dict["current_ep_num"] = ep_num
                        reporter.state.result_data = {"pipeline_type": "writing", "context": state_dict}
                        reporter.state._save_to_db()
                    return ctx.total_chars, ctx.failed_episodes

        return ctx.total_chars, ctx.failed_episodes
