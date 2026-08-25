import logging
from typing import Optional

from huey import crontab

from src.core.container import AppContainer
from config.container import get_container
from prompts.manager import prompt_manager
from src.backend.database.uow import UnitOfWork
from src.core.observability import with_trace_context
from src.backend.worker_config import huey
from src.backend.redis_util import get_redis_client

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
        "planner": container.planning_service(),
        "writing": container.writer(),
        "writing_service": container.writing_service(),
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
def execute_service_workflow(task_id: str, api_key: str, config_dict: dict, method_name: str, kwargs: dict, trace_id: Optional[str] = None):
    import asyncio
    from src.backend.background import BackgroundReporter, ProgressState

    state = ProgressState(is_running=True, task_id=task_id, repo=None)
    reporter = BackgroundReporter(state)

    async def _run():
        try:
            from src.core.container import AppContainer
            from src.core.container import make_container

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
    from src.core.container import AppContainer
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
    from src.core.container import AppContainer
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


@huey.task(retries=3, retry_delay=5)
@with_trace_context
def execute_easy_mode_generation(task_id: str, api_key: str, genre: str, keywords: str, archetype_key: str, target_eps: int, initial_limit: int, word_count: int, concept: str, tone_vibe: float, style_key: Optional[str], enable_erotic: bool, erotic_intensity: int, trace_id: Optional[str] = None):
    """かんたんモード全自動生成をバックグラウンドで実行するタスク"""
    import asyncio
    from src.backend.background import BackgroundReporter, ProgressState
    from src.backend.task_helpers import create_easy_mode_pipeline, run_pipeline_with_progress, get_engine_for_task, create_pipeline_config_from_params
    from config.settings import get_settings

    state = ProgressState(is_running=True, task_id=task_id, repo=None)
    reporter = BackgroundReporter(state)

    async def _run():
        try:
            # エンジンを取得
            engine = get_engine_for_task(api_key)

            # 設定を作成（ヘルパー関数を使用）
            config = create_pipeline_config_from_params(genre, target_eps)

            # ヘルパー関数を使ってパイプラインを作成・実行
            pipeline = create_easy_mode_pipeline(engine, config)
            result = await run_pipeline_with_progress(pipeline, state)

            # 完了処理
            state.is_running = False
            state.message = "生成完了"
            state.result_data = {
                "title": result.title,
                "concept": result.concept,
                "total_episodes": result.total_episodes,
                "total_words": sum(ep.word_count for ep in result.episodes),
                "average_audit_score": round(sum(ep.audit_score for ep in result.episodes) / len(result.episodes), 1) if result.episodes else 0,
                "genre": result.genre,
                "episodes": [
                    {
                        "episode_num": ep.episode_num,
                        "title": ep.title,
                        "word_count": ep.word_count,
                        "audit_score": ep.audit_score,
                        "audit_passed": ep.audit_passed,
                        "rewrite_count": ep.rewrite_count,
                        "needs_human_review": ep.needs_human_review,
                    }
                    for ep in result.episodes
                ],
            }
            state._save_to_db()

            logger.info(f"Easy mode pipeline completed: {task_id}")

        except Exception as e:
            logger.error(f"Easy mode pipeline failed: {e}", exc_info=True)
            state.is_running = False
            state.error = str(e)
            state._save_to_db()

    try:
        asyncio.run(_run())
    except Exception as e:
        logger.error(f"Task execution failed: {e}", exc_info=True)