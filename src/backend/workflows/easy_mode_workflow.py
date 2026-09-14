"""
EasyModeWorkflow - 統合パイプラインへ委譲
既存インターフェース完全互換維持
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from src.backend.workflows.base_workflow import BaseWorkflow
from src.services.auto_workflow_pipeline import create_easy_mode_pipeline
from src.services.pipeline_param_mapper import (
    map_context_to_easymode_result,
    map_easymode_kwargs_to_context,
)
from src.services.progress_reporter import ProgressReporterAdapter
from src.shared.utils import StatusReporter

USE_UNIFIED = os.getenv("USE_UNIFIED_PIPELINE", "1") == "1"

logger = logging.getLogger(__name__)


class EasyModeWorkflow(BaseWorkflow):
    """
    かんたんモードの全自動小説生成パイプラインを実行するワークフロー。
    統合パイプライン (AutoWorkflowPipeline) に委譲。
    """

    async def _save_checkpoint(self, book_id: int, last_completed_ep: int, compressed_context: dict[str, Any] | None = None) -> None:
        """チェックポイントを保存する"""
        checkpoint_data = {
            "last_completed_ep": last_completed_ep,
            "compressed_context": compressed_context,
            "updated_at": datetime.now().isoformat(),
        }
        await self.repo.set_state(f"easy_mode_checkpoint_{book_id}", checkpoint_data)
        logger.debug(f"Checkpoint saved for book {book_id}: episode {last_completed_ep}")

    async def _load_checkpoint(self, book_id: int) -> tuple[int, dict[str, Any] | None]:
        """チェックポイントを読み込む。返り値: (last_completed_ep, compressed_context)"""
        checkpoint_data = await self.repo.get_state(f"easy_mode_checkpoint_{book_id}")
        if checkpoint_data:
            last_completed_ep = checkpoint_data.get("last_completed_ep", 0)
            compressed_context = checkpoint_data.get("compressed_context")
            logger.debug(f"Checkpoint loaded for book {book_id}: episode {last_completed_ep}")
            return last_completed_ep, compressed_context
        return 0, None

    async def execute(
        self,
        reporter: StatusReporter,
        genre: str = "ファンタジー",
        keywords: list[str] | None = None,
        protagonist_type: str = "チート主人公",
        target_episodes: int = 10,
        words_per_episode: int = 2000,
        enable_audit: bool = True,
        max_rewrites: int = 2,
        start_ep: int = 1,
        end_ep: int | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        logger.info(f"EasyModeWorkflow started: genre={genre}, target_episodes={target_episodes}")

        if not USE_UNIFIED:
            raise NotImplementedError(
                "USE_UNIFIED_PIPELINE=0 is no longer supported. "
                "The legacy implementation was removed in the pipeline unification. "
                "Use USE_UNIFIED_PIPELINE=1 (default)."
            )

        # 1. 統合パイプライン用 Context 構築
        ctx = map_easymode_kwargs_to_context(
            genre=genre,
            keywords=keywords,
            protagonist_type=protagonist_type,
            target_episodes=target_episodes,
            words_per_episode=words_per_episode,
            enable_audit=enable_audit,
            max_rewrites=max_rewrites,
            start_ep=start_ep,
            end_ep=end_ep,
            **kwargs,
        )

        # 2. チェックポイントからコンテキストを復元（もしあれば）
        book_id_from_ctx = kwargs.get("book_id")
        if book_id_from_ctx is not None:
            _, compressed_context = await self._load_checkpoint(book_id_from_ctx)
            if compressed_context is not None:
                ctx.easy_parameters["compressed_context"] = compressed_context
                logger.debug(f"Loaded compressed context for book {book_id_from_ctx}")

        # 3. 既存の書籍がある場合、完了済みエピソード数をチェックして開始位置を調整
        # book_idがkwargsに含まれている場合（EasyModeInputから渡される）
        book_id = kwargs.get("book_id")
        if book_id is not None and start_ep == 1:  # デフォルト値の場合のみ自動調整
            try:
                # 既存のエピソード数を取得
                chapters = await self.repo.chapters.get_all_non_anchor_chapters(book_id)
                if chapters:
                    max_completed_ep = max(ch.ep_num for ch in chapters)
                    if max_completed_ep > 0:
                        # 開始位置を調整（ただし、end_epが指定されている場合はそれを尊重）
                        adjusted_start_ep = max_completed_ep + 1
                        if end_ep is None or adjusted_start_ep <= end_ep:
                            logger.info(f"Resuming from episode {adjusted_start_ep} (completed {max_completed_ep} episodes)")
                            ctx.start_ep = adjusted_start_ep
                        else:
                            logger.info(f"All episodes already completed (up to {max_completed_ep}), nothing to do")
                            # すべて完了している場合は早期終了
                            return {
                                "title": "",
                                "concept": "",
                                "total_episodes": 0,
                                "total_words": 0,
                                "average_audit_score": 0.0,
                                "genre": genre,
                                "episodes": [],
                                "status": "completed",
                            }
            except ValueError:
                # max() argument is an empty sequence
                pass
            except Exception as e:
                logger.warning(f"Failed to check existing episodes: {e}")
                # エラーが発生した場合はデフォルトの動作を続行

        # 3. パイプライン構築・実行
        pipeline = create_easy_mode_pipeline(
            genre=genre,
            target_episodes=target_episodes,
            enable_spice_guard=enable_audit,
            max_rewrite_iterations=max_rewrites,
            target_audit_score=95.0,
            enable_marketing=True,
        )

        adapter = ProgressReporterAdapter(reporter, is_easy_mode=True)
        result = await pipeline.execute(ctx, self.engine, adapter)

        # 4. チェックポイントを保存（成功時のみ）
        if result.get("status") == "success":
            last_completed_ep = ctx.end_ep or ctx.target_eps
            await self._save_checkpoint(
                book_id=ctx.book_id,
                last_completed_ep=last_completed_ep,
                compressed_context=None  # TODO: Implement context compression in later step
            )
            logger.info(f"Checkpoint saved: book {ctx.book_id}, up to episode {last_completed_ep}")

        # 5. 既存インターフェース互換の dict に変換
        return map_context_to_easymode_result(ctx, result)


__all__ = ["EasyModeWorkflow"]
