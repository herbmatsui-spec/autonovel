"""AutoNovel tasks package."""

import logging

from huey import crontab

from src.backend.tasks.generation_tasks import generate_chapter_task
from src.backend.tasks.huey import huey
from src.core.observability import with_trace_context

logger = logging.getLogger(__name__)

_CONFIG_OVERRIDE_KEYS = (
    "anti_repetition_penalty",
    "repetition_penalty",
    "frequency_penalty",
    "presence_penalty",
    "temperature",
    "top_p",
    "top_k",
    "max_tokens",
    "model",
)


def _apply_config_overrides(config_dict: dict | None) -> None:
    if not config_dict:
        return
    try:
        from config.project_context import ProjectContext

        for key in _CONFIG_OVERRIDE_KEYS:
            if key in config_dict and config_dict[key] not in (None, ""):
                ProjectContext.set_setting(key, config_dict[key])
    except Exception as e:
        logger.warning(f"Failed to apply config overrides: {e}")


@huey.task(retries=3, retry_delay=5)
@with_trace_context
def process_vector_event(event_type: str, payload: dict, trace_id: str | None = None):
    """非同期でChromaDBへの操作を実行するタスク"""
    logger.info(f"Processing vector event: {event_type}")
    from src.services.vector_store import DefaultVectorStore

    store = DefaultVectorStore()

    if event_type == "chroma_add":
        return store.add_documents(
            collection_name=payload["collection"],
            ids=[payload["id"]],
            documents=[payload["content"]],
            embeddings=[payload["embedding"]],
            metadatas=[payload["metadata"]] if payload["metadata"] else None,
        )
    elif event_type == "chroma_delete":
        return store.delete_by_id(collection_name=payload["collection"], ids=payload["ids"])
    return None


@huey.periodic_task(crontab(minute="*"))
def process_outbox_events():
    """Huey periodic task for processing Outbox events."""
    logger.info("Running outbox processor task...")
    import asyncio

    try:
        asyncio.run(_process_outbox_events_async())
    except Exception as e:
        logger.error(f"Failed to process outbox events: {e}")


async def _process_outbox_events_async():
    from src.backend.database.uow import UnitOfWork
    from src.core.container import AppContainer

    db = AppContainer.db()

    async with UnitOfWork(db=db) as uow:
        events = await uow.get_pending_outbox_events()

    for event in events:
        try:
            async with UnitOfWork(db=db) as event_uow:
                await event_uow.mark_outbox_event_processed(event.id)
        except Exception as e:
            logger.error(f"Failed to process outbox event {event.id}: {e}")


def _create_workflow(method_name: str, **services):
    """WORKFLOW_REGISTRY からワークフローを検索しインスタンス化する。"""
    from src.backend.workflows import WORKFLOW_REGISTRY

    workflow_cls = WORKFLOW_REGISTRY.get(method_name)
    if workflow_cls is None:
        raise ValueError(f"Unknown workflow method: {method_name}")
    return workflow_cls(**services)


def _build_service_dict(container):
    """コンテナからワークフローに必要な全サービスを取得して辞書として返す。"""
    engine = container.engine()
    return {
        "planner": container.planner(),
        "writing": container.writer(),
        "repo": container.repo(),
        "critique": container.critique(),
        "narrative": container.narrative(),
        "marketing": container.marketing(),
        "bible_agent": container.bible_generator(),
        "plot_agent": container.plot_expander(),
        "formatter": container.formatter(),
        "vector_store": container.vector_store(),
        "llm_client": container.genai_client(),
        "tension": engine,
        "image_service": container.image_service(),
        "illustration_agent": container.illustration_agent(),
        "illustration_workflow": container.illustration_workflow(),
    }


@huey.task(retries=3, retry_delay=5)
@with_trace_context
def execute_service_workflow(
    task_id: str,
    api_key: str,
    config_dict: dict,
    method_name: str,
    kwargs: dict,
    trace_id: str | None = None,
):
    import asyncio

    from src.backend.background import BackgroundReporter, ProgressState

    state = ProgressState(is_running=True, task_id=task_id, repo=None)
    reporter = BackgroundReporter(state)

    async def _run():
        try:
            from src.core.container import AppContainer

            _apply_config_overrides(config_dict)

            container = AppContainer(
                api_key=api_key,
                db=AppContainer.db(),
            )

            services = _build_service_dict(container)
            state.repo = services["repo"]

            workflow = _create_workflow(method_name, **services)
            res = await workflow.execute(reporter, **kwargs)

            state.result_data = res
            state.is_running = False
            state.message = "処理が完了しました。"
            state._save_to_db()

        except Exception as e:
            logger.error(f"Workflow error: {e}", exc_info=True)
            state.is_running = False
            state.error = str(e)
            state._save_to_db()

    try:
        asyncio.run(_run())
    except Exception as e:
        logger.error(f"Task execution failed: {e}", exc_info=True)


@huey.task(retries=3, retry_delay=5)
@with_trace_context
def run_test_coro(task_id: str, message: str, trace_id: str | None = None):
    """テスト用のダミータスク"""
    from src.backend.background import ProgressState
    from src.core.container import AppContainer

    db = AppContainer.db()

    class FakeEngine:
        def __init__(self):
            self.db = db

    state = ProgressState(
        is_running=False, task_id=task_id, repo=FakeEngine(), skip_initial_save=True
    )
    state.result_data = "SuccessValue"
    state.logs = [message]
    state._save_to_db()


@huey.task(retries=3, retry_delay=5)
@with_trace_context
def async_score_narrative_metrics(
    book_id: int, branch_id: int, ep_num: int, trace_id: str | None = None
):
    """エピソードのスコアリングをバックグラウンドで実行するタスク"""
    import asyncio

    from src.backend.database.repositories.narrative_metrics_repo import NarrativeMetricRepository
    from src.services.narrative_scoring_service import NarrativeScoringService

    async def _run():
        try:
            from src.core.container import AppContainer

            container = AppContainer()
            db = container.db()
            auditor = container.auditor()
            async with db.get_session() as session:
                metrics_repo = NarrativeMetricRepository(session)
                service = NarrativeScoringService(session, auditor, metrics_repo)
                success = await service.rescore_episode(book_id, branch_id, ep_num)
                logger.info(f"Background scoring for Ep.{ep_num} finished. Success: {success}")
                return success
        except Exception as e:
            logger.exception(f"Error in async_score_narrative_metrics for Ep.{ep_num}: {e}")
            return False

    return asyncio.run(_run())


@huey.task(retries=3, retry_delay=5)
@with_trace_context
def enqueue_audit_after_write(
    book_id: int, write_from: int, write_to: int, trace_id: str | None = None
):
    """執筆完了後の論理監査 (Shadow Mode) をバックグラウンドで実行するタスク。"""
    import asyncio

    async def _run():
        try:
            from src.core.container import AppContainer

            container = AppContainer()
            db = container.db()
            auditor = container.auditor()
            async with db.get_session() as session:
                for ep_num in range(write_from, write_to + 1):
                    await auditor.audit_episode(session, book_id, ep_num)
                logger.info(
                    f"Shadow audit finished for book_id={book_id}, ep{write_from}-ep{write_to}"
                )
        except Exception as e:
            logger.exception(f"Error in enqueue_audit_after_write for book_id={book_id}: {e}")

    return asyncio.run(_run())


__all__ = [
    "huey",
    "generate_chapter_task",
    "process_vector_event",
    "process_outbox_events",
    "execute_service_workflow",
    "run_test_coro",
    "async_score_narrative_metrics",
    "enqueue_audit_after_write",
]
