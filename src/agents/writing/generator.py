# src/agents/writing/generator.py
"""WritingGenerator - 本文生成の実装ロジック"""
from __future__ import annotations

import logging
from typing import Any

from src.agents.episode_pipeline import EpisodePipeline
from src.agents.scheduler_coordinator import SchedulerCoordinator

logger = logging.getLogger(__name__)


class WritingGenerator:
    """本文生成ジェネレーター（EpisodePipeline と連携）"""

    def __init__(
        self,
        repo: Any = None,
        llm: Any = None,
        pm: Any = None,
        style_rag: Any = None,
        ctx_mgr: Any = None,
        reporter_factory: Any = None,
        plot_expander: Any = None,
    ):
        self.repo = repo
        self.llm = llm
        self.pm = pm
        self.style_rag = style_rag
        self.ctx_mgr = ctx_mgr
        self.reporter_factory = reporter_factory
        self.plot_expander = plot_expander
        self.branch_id = 1

        # 必要な属性を設定（SchedulerCoordinator が期待するもの）
        self.prompt_manager = pm
        self._writing_graph_manager = None

    def _get_bible(self, book_id: int) -> Any:
        """Bible を取得（SchedulerCoordinator 用）"""
        if self.repo is None:
            return None
        try:
            return self.repo.get_latest_bible(book_id)
        except Exception as e:
            logger.debug(f"Failed to get bible for book_id={book_id}: {e}")
            return None

    async def generate_episodes_pipeline(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
        passion: float,
        target_word_count: int,
        is_easy_mode: bool,
        reporter: Any,
        branch_id: int = 1,
        style_tag: Any = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        """エピソード生成パイプラインを実行"""
        self.branch_id = branch_id

        # EpisodePipeline に自分自身を渡して実行
        pipeline = EpisodePipeline(self)
        return await pipeline.run(
            book_id=book_id,
            start_ep=start_ep,
            end_ep=end_ep,
            passion=passion,
            target_word_count=target_word_count,
            is_easy_mode=is_easy_mode,
            reporter=reporter,
            branch_id=branch_id,
            style_tag=style_tag,
        )

    async def generate_episodes(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
        passion: float,
        target_word_count: int,
        is_easy_mode: bool,
        reporter: Any,
        branch_id: int = 1,
        style_tag: Any = None,
    ) -> int:
        """単発エピソード生成（EpisodePipeline 経由）"""
        result = await self.generate_episodes_pipeline(
            book_id=book_id,
            start_ep=start_ep,
            end_ep=end_ep,
            passion=passion,
            target_word_count=target_word_count,
            is_easy_mode=is_easy_mode,
            reporter=reporter,
            branch_id=branch_id,
            style_tag=style_tag,
        )
        return result[0]  # total_chars

    async def analyze_and_import_chapter(
        self,
        book_id: int,
        ep_num: int,
        import_text: str,
        do_refine: bool = True,
    ) -> Any:
        """手書き原稿のインポート・研磨（未実装）"""
        raise NotImplementedError("analyze_and_import_chapter is not implemented yet")


# 後方互換性のためのエイリアス
class WritingAgent:
    """後方互換性のためのエイリアス（EngineFacade 等から呼ばれる）"""

    def __init__(
        self,
        repo: Any = None,
        llm: Any = None,
        style_rag: Any = None,
        plot_expander: Any = None,
        **kwargs,
    ):
        self.generator = WritingGenerator(
            repo=repo,
            llm=llm,
            style_rag=style_rag,
            plot_expander=plot_expander,
            **kwargs,
        )
        # EpisodePipeline が期待する属性
        self.repo = repo
        self.llm = llm
        self.style_rag = style_rag
        self.plot_expander = plot_expander
        self.prompt_manager = kwargs.get("pm")
        self.branch_id = 1
        self._writing_graph_manager = None

    def _get_bible(self, book_id: int) -> Any:
        return self.generator._get_bible(book_id)

    async def generate_episodes_pipeline(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
        passion: float,
        target_word_count: int,
        is_easy_mode: bool,
        reporter: Any,
        branch_id: int = 1,
        style_tag: Any = None,
    ) -> tuple[int, list[dict[str, Any]]]:
        return await self.generator.generate_episodes_pipeline(
            book_id=book_id,
            start_ep=start_ep,
            end_ep=end_ep,
            passion=passion,
            target_word_count=target_word_count,
            is_easy_mode=is_easy_mode,
            reporter=reporter,
            branch_id=branch_id,
            style_tag=style_tag,
        )

    async def generate_episodes(
        self,
        book_id: int,
        start_ep: int,
        end_ep: int,
        passion: float,
        target_word_count: int,
        is_easy_mode: bool,
        reporter: Any,
        branch_id: int = 1,
        style_tag: Any = None,
    ) -> int:
        return await self.generator.generate_episodes(
            book_id=book_id,
            start_ep=start_ep,
            end_ep=end_ep,
            passion=passion,
            target_word_count=target_word_count,
            is_easy_mode=is_easy_mode,
            reporter=reporter,
            branch_id=branch_id,
            style_tag=style_tag,
        )

    async def analyze_and_import_chapter(
        self,
        book_id: int,
        ep_num: int,
        import_text: str,
        do_refine: bool = True,
    ) -> Any:
        return await self.generator.analyze_and_import_chapter(
            book_id=book_id,
            ep_num=ep_num,
            import_text=import_text,
            do_refine=do_refine,
        )