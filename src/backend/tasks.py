import logging
from typing import Optional

from huey import SqliteHuey, crontab

from config.container import Container
from prompts.manager import prompt_manager
from src.backend.database.uow import UnitOfWork
from src.core.observability import with_trace_context

huey = SqliteHuey('kaku_hegemony_v2_huey.db')
logger = logging.getLogger('huey')

_CONFIG_OVERRIDE_KEYS = {
    "model_planning",
    "model_plot_expansion",
    "model_writing",
    "model_climax",
    "model_stable_fallback",
    "model_ultra_stable",
    "model_embedding",
    "openai_base_url",
    "openai_api_key",
}


def _apply_config_overrides(config_dict: Optional[dict]) -> None:
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
def process_vector_event(event_type: str, payload: dict, trace_id: Optional[str] = None):
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
            metadatas=[payload["metadata"]] if payload["metadata"] else None
        )
    elif event_type == "chroma_delete":
        return store.delete_by_id(
            collection_name=payload["collection"],
            ids=payload["ids"]
        )
    return None


@huey.periodic_task(crontab(minute='*'))
def process_outbox_events():
    """Huey periodic task for processing Outbox events."""
    logger.info("Running outbox processor task...")
    import asyncio
    try:
        asyncio.run(_process_outbox_events_async())
    except Exception as e:
        logger.error(f"Failed to process outbox events: {e}")


async def _process_outbox_events_async():
    container = get_container()
    db = container.db()
    uow = UnitOfWork(db=db)

    async with uow:
        events = await uow.get_pending_outbox_events()
        for event in events:
            try:
                await uow.mark_outbox_event_processed(event.id)
            except Exception as e:
                logger.error(f"Failed to process outbox event {event.id}: {e}")


@huey.task(retries=3, retry_delay=5)
@with_trace_context
def execute_service_workflow(task_id: str, api_key: str, config_dict: dict, method_name: str, kwargs: dict, trace_id: Optional[str] = None):
    import asyncio
    from src.backend.background import BackgroundReporter, ProgressState

    state = ProgressState(is_running=True, task_id=task_id, repo=None)
    reporter = BackgroundReporter(state)

    async def _run():
        try:
            from dependency_injector import providers
from config.container import Container, get_container
            from src.core.container import AppContainer

            _apply_config_overrides(config_dict)

            container = AppContainer(
                api_key=providers.Object(api_key),
                db=providers.Object(Container.db())
            )
            engine = container.engine()
            state.repo = engine.repo

            if method_name == "full_auto_workflow":
                from src.backend.workflows.full_auto_workflow import FullAutoWorkflow
                workflow = FullAutoWorkflow(engine)
            elif method_name == "episode_writing_workflow":
                from src.backend.workflows.episode_writing_workflow import EpisodeWritingWorkflow
                workflow = EpisodeWritingWorkflow(engine)
            elif method_name == "plan_generation_workflow":
                from src.backend.workflows.plan_generation_workflow import PlanGenerationWorkflow
                workflow = PlanGenerationWorkflow(engine)
            elif method_name == "plot_expansion_workflow":
                from src.backend.workflows.plot_expansion_workflow import PlotExpansionWorkflow
                workflow = PlotExpansionWorkflow(engine)
            elif method_name == "plot_rebuild_workflow":
                from src.backend.workflows.plot_rebuild_workflow import PlotRebuildWorkflow
                workflow = PlotRebuildWorkflow(engine)
            elif method_name == "run_critique_optimization_workflow":
                from src.backend.workflows.critique_optimization_workflow import (
                    CritiqueOptimizationWorkflow,
                )
                workflow = CritiqueOptimizationWorkflow(engine)
            elif method_name == "retry_failed_episodes_workflow":
                from src.backend.workflows.retry_failed_episodes_workflow import (
                    RetryFailedEpisodesWorkflow,
                )
                workflow = RetryFailedEpisodesWorkflow(engine)
            elif method_name == "chapter_import_workflow":
                from src.backend.workflows.chapter_import_workflow import ChapterImportWorkflow
                workflow = ChapterImportWorkflow(engine)
            elif method_name == "marketing_generation_workflow":
                from src.backend.workflows.marketing_generation_workflow import (
                    MarketingGenerationWorkflow,
                )
                workflow = MarketingGenerationWorkflow(engine)
            elif method_name == "refine_erotic_workflow":
                from src.backend.workflows.refine_erotic_workflow import RefineEroticWorkflow
                workflow = RefineEroticWorkflow(engine)
            else:
                raise ValueError(f"Unknown workflow method: {method_name}")

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
def run_test_coro(task_id: str, message: str, trace_id: Optional[str] = None):
    """テスト用のダミータスク"""
    container = get_container()
    db = container.db()

    class FakeEngine:
        def __init__(self):
            self.db = db

    state = ProgressState(is_running=False, task_id=task_id, repo=FakeEngine(), skip_initial_save=True)
    state.result_data = "SuccessValue"
    state.logs = [message]
    state._save_to_db()


@huey.task(retries=3, retry_delay=5)
@with_trace_context
def async_score_narrative_metrics(book_id: int, branch_id: int, ep_num: int, trace_id: Optional[str] = None):
    """エピソードのスコアリングをバックグラウンドで実行するタスク"""
    import asyncio
    from config.container import Container
    from src.agents.audit import LogicalAuditor
    from src.backend.database.repositories.narrative_metrics_repo import NarrativeMetricRepository
    from src.services.narrative_scoring_service import NarrativeScoringService

    async def _run():
        try:
            container = get_container()
            async with container.async_session() as session:
                auditor = LogicalAuditor(
                    repo=container.repo_plot(),
                    pm=container.prompt_manager(),
                    generate_json=container.llm().generate_json,
                    ctx_mgr=container.project_context()
                )
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
def enqueue_audit_after_write(book_id: int, write_from: int, write_to: int, trace_id: Optional[str] = None):
    """執筆完了後の論理監査 (Shadow Mode) をバックグラウンドで実行するタスク。"""
    import asyncio
    from config.container import Container
    from src.agents.audit import LogicalAuditor

    async def _run():
        try:
            container = get_container()
            async with container.async_session() as session:
                auditor = LogicalAuditor(
                    repo=container.repo_plot(),
                    pm=container.prompt_manager(),
                    generate_json=container.llm().generate_json,
                    ctx_mgr=container.project_context(),
                )
                for ep_num in range(write_from, write_to + 1):
                    await auditor.audit_episode(session, book_id, ep_num)
                logger.info(
                    f"Shadow audit finished for book_id={book_id}, ep{write_from}-ep{write_to}"
                )
        except Exception as e:
            logger.exception(f"Error in enqueue_audit_after_write for book_id={book_id}: {e}")

    return asyncio.run(_run())
