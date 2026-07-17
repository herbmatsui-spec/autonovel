import logging
from typing import Any, Dict

from src.shared.utils import StatusReporter

from ._shared_ops import enqueue_shadow_audit, trigger_prefetch
from .base_workflow import BaseWorkflow

logger = logging.getLogger(__name__)


class EpisodeWritingWorkflow(BaseWorkflow):
    """執筆ワークフロー: 通常モードとパイプラインモードの切り替えを隠蔽"""
    async def execute(self, reporter: StatusReporter, **kwargs) -> Dict[str, Any]:
        book_id = kwargs["book_id"]
        write_from = kwargs["write_from"]
        write_to = kwargs["write_to"]
        passion = kwargs["passion"]
        word_count = kwargs["word_count"]
        do_refine = kwargs["do_refine"]
        env_state = kwargs["env_state"]
        pipeline_mode = kwargs["pipeline_mode"]
        mode = kwargs.get("mode", "final")

        # WritingService を使用（engine.writer から移行済）
        writing = self.writing

        if pipeline_mode:
            chars_count, failed = await writing.generate_episodes_pipeline(
                book_id, write_from, write_to, passion, word_count, reporter=reporter,
                mode=mode
            )
            # 執筆完了後にプリフェッチを実行して次のエピソード生成を高速化
            await self._trigger_prefetch(book_id, write_to, reporter)
            # 非同期で監査を走らせる (Shadow Mode)
            try:
                from src.backend.tasks import enqueue_audit_after_write
                enqueue_audit_after_write(book_id, write_from, write_to)
                reporter.report("⚖️ 非同期の論理監査タスク (Shadow Mode) をエンキューしました。", "info")
            except Exception as e:
                logger.error(f"Failed to enqueue shadow audit: {e}")
            return {"chars_count": chars_count, "failed_episodes": failed, "book_id": book_id}
        else:
            chars_count = await writing.generate_episodes(
                book_id, write_from, write_to, passion, word_count, do_refine,
                reporter=reporter, env_state=env_state, mode=mode
            )
            # 執筆完了後にプリフェッチを実行して次のエピソード生成を高速化
            await self._trigger_prefetch(book_id, write_to, reporter)
            # 非同期で監査を走らせる (Shadow Mode)
            try:
                from src.backend.tasks import enqueue_audit_after_write
                enqueue_audit_after_write(book_id, write_from, write_to)
                reporter.report("⚖️ 非同期の論理監査タスク (Shadow Mode) をエンキューしました。", "info")
            except Exception as e:
                logger.error(f"Failed to enqueue shadow audit: {e}")
            return {"chars_count": chars_count, "book_id": book_id}

    async def _trigger_prefetch(self, book_id: int, last_episode: int, reporter: StatusReporter) -> None:
        """
        執筆完了後に Semantic Cache のプリフェッチ機能を起動し、
        次のエピソード群のEmbeddingを先行計算してキャッシュをウォームアップする。
        """
        try:
            from src.services.semantic_cache import SemanticCacheManager

            # SemanticCacheManager のインスタンスを取得
            # (Container 等でインジェクションされている場合はそれを使用)
            vector_store = getattr(self.engine, "vector_store", None)
            client = getattr(self.engine, "llm_client", None) or getattr(self.engine, "client", None)

            if not vector_store or not client:
                # VectorStore/Client が Engine に注入されていない場合はスキップ
                logger.debug("[PREFETCH] VectorStore or Client not available, skipping prefetch")
                return

            cache_manager = SemanticCacheManager(vector_store=vector_store, client=client)

            # 次の3エピソード分のプリフェッチを非同期実行
            prefetch_task_types = ["drafting", "polishing"]
            next_ep = last_episode + 1

            # バックグラウンドでプリフェッチを実行（執筆をブロックしない）
            import asyncio
            asyncio.create_task(
                cache_manager.prefetch_by_pattern(
                    book_id=book_id,
                    ep_range_start=next_ep,
                    ep_range_end=min(next_ep + 2, next_ep + 3),  # 次の3話まで
                    task_types=prefetch_task_types,
                )
            )
            reporter.report(f"🚀 Prefetch triggered for ep{next_ep}-ep{next_ep+2} (background)", "debug")
            logger.info(f"[PREFETCH] Triggered for book_id={book_id}, ep{next_ep}-ep{next_ep+2}")
        except Exception as e:
            # プリフェッチ失敗は致命的なエラーではなくログ出力のみ
            logger.warning(f"[PREFETCH] Prefetch trigger failed: {e}")
