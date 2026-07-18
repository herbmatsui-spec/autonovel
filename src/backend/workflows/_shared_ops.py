import logging
from typing import Any, List, Tuple

from src.shared.utils import StatusReporter

logger = logging.getLogger(__name__)

async def enqueue_shadow_audit(book_id: int, write_from: int, write_to: int, reporter: StatusReporter) -> None:
    """非同期の論理監査タスク (Shadow Mode) をエンキューする"""
    try:
        from src.backend.tasks import enqueue_audit_after_write
        enqueue_audit_after_write(book_id, write_from, write_to)
        reporter.report("⚖️ 非同期の論理監査タスク (Shadow Mode) をエンキューしました。", "info")
    except Exception as e:
        logger.error(f"Failed to enqueue shadow audit: {e}")

async def trigger_prefetch(engine, book_id: int, last_episode: int, reporter: StatusReporter) -> None:
    """執筆完了後に Semantic Cache のプリフェッチ機能を起動する"""
    try:
        from src.services.semantic_cache import SemanticCacheManager

        vector_store = getattr(engine, "vector_store", None)
        client = getattr(engine, "llm_client", None) or getattr(engine, "client", None)

        if not vector_store or not client:
            logger.debug("[PREFETCH] VectorStore or Client not available, skipping prefetch")
            return

        cache_manager = SemanticCacheManager(vector_store=vector_store, client=client)

        prefetch_task_types = ["drafting", "polishing"]
        next_ep = last_episode + 1

        import asyncio
        asyncio.create_task(
            cache_manager.prefetch_by_pattern(
                book_id=book_id,
                ep_range_start=next_ep,
                ep_range_end=min(next_ep + 2, next_ep + 3),
                task_types=prefetch_task_types,
            )
        )
        reporter.report(f"🚀 Prefetch triggered for ep{next_ep}-ep{next_ep+2} (background)", "debug")
        logger.info(f"[PREFETCH] Triggered for book_id={book_id}, ep{next_ep}-ep{next_ep+2}")
    except Exception as e:
        logger.warning(f"[PREFETCH] Prefetch trigger failed: {e}")

async def run_pipeline_with_retry(writer, book_id: int, start_ep: int, end_ep: int, passion: float, word_count: int, reporter, is_easy_mode: bool = True, max_retries: int = 1) -> Tuple[int, List[Any]]:
    """エピソード生成パイプラインを実行し、必要に応じて自動リトライする"""
    total_chars, failed = await writer.generate_episodes_pipeline(
        book_id=book_id, start_ep=start_ep, end_ep=end_ep, passion=passion, 
        target_word_count=word_count, reporter=reporter, is_easy_mode=is_easy_mode
    )
    
    for _ in range(max_retries):
        if not failed or reporter.state.should_stop():
            break
            
        reporter.report(f"🔄 {len(failed)}件のエピソードで不備を検知。自動修復中...", "warning")
        retry_chars, still_failed = await writer.generate_episodes_pipeline(
            book_id=book_id, start_ep=start_ep, end_ep=end_ep, passion=passion, 
            target_word_count=word_count, reporter=reporter, is_easy_mode=is_easy_mode
        )
        total_chars += retry_chars
        failed = still_failed
        
    return total_chars, failed
