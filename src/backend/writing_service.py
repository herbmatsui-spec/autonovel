"""
writing_service.py - WritingService: 本文執筆・研磨を担当するドメインサービス。

UltimateHegemonyEngine の UltimateHegemonyEngine から分離したサービス。
Workflows (EpisodeWritingWorkflow, ChapterImportWorkflow, RetryFailedEpisodesWorkflow,
RefineEroticWorkflow 等) は WritingService を依存対象にし、EngineFacade 経由で
インジェクトされる。

主な責任:
- generate_episodes_pipeline: パイプライン執筆（WritingAgent へ委譲）
- generate_episodes: 単発執筆（WritingAgent へ委譲）
- analyze_and_import_chapter: 手書き原稿インポート（委譲先があれば）
"""
from typing import Any, List, Optional, Tuple

from src.backend.protocols import WritingPort
from src.shared.utils import StatusReporter


class WritingService:
    """覇権小説の本文執筆・研磨を担当するサービス。"""

    def __init__(
        self,
        writer: Any,  # WritingAgent 実体
        repo: Any,  # DataRepository
        pm: Any,  # PromptManager
        style_rag: Any,  # StyleRagManager
        ctx_mgr: Any,  # ContextManager
        reporter_factory: Any,  # StatusReporter 作成用 Callable
    ) -> None:
        self.writer = writer
        self.repo = repo
        self.pm = pm
        self.style_rag = style_rag
        self.ctx_mgr = ctx_mgr
        self.reporter_factory = reporter_factory

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
    ) -> Tuple[int, List[Any]]:
        """
        エピソード生成パイプラインを実行する。
        実際の実行は writer.generate_episodes_pipeline に委譲。
        """
        return await self.writer.generate_episodes_pipeline(
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
        """
        単発のエピソード執筆を実行する。
        実際の実行は writer.generate_episodes に委譲。
        """
        return await self.writer.generate_episodes(
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
        """
        手書き原稿のインポート・研磨を実行する。
        writer が analyze_and_import_chapter を持っていれば委譲、
        持っていなければ NotImplementedError を送出（呼び出し側で要ハンドリング）。
        """
        method = getattr(self.writer, "analyze_and_import_chapter", None)
        if method is None:
            raise NotImplementedError(
                "WritingAgent に analyze_and_import_chapter が実装されていません。"
                "ChapterImportWorkflow の実行には当該メソッドが必要です。"
            )
        return await method(
            book_id=book_id,
            ep_num=ep_num,
            import_text=import_text,
            do_refine=do_refine,
        )
