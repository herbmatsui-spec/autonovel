import ipaddress
import logging
from typing import Optional
from urllib.parse import urlparse

from huey import crontab

from config.container import get_container
from src.backend.background import ProgressState
from src.backend.database.uow import UnitOfWork
from src.backend.worker_config import huey
from src.core.container import AppContainer
from src.core.observability import with_trace_context

logger = logging.getLogger('huey')

_NO_VALUE = object()

# Configuration keys that may be overridden via task request payloads.
# This mirrors the whitelist used by the original ProjectContext implementation.
# Extend as needed for additional configurable parameters.
_CONFIG_OVERRIDE_KEYS = [
    "openai_base_url",
    "openai_api_key",
    "gemini_api_key",
    "inference_top_p",
    "inference_top_k",
    "system_sandbox",
]

# openai_base_url はリクエスト越しに指定可能だが、SSRF 回避のため
# プライベート/ループバック/予約アドレス宛は拒否する。
def _is_safe_base_url(value: str) -> bool:
    try:
        parsed = urlparse(value)
    except (ValueError, TypeError):
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    host = (parsed.hostname or "").strip().lower()
    if not host:
        return False
    if host in ("localhost", "0.0.0.0", "::1"):
        return False
    try:
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            return False
    except ValueError:
        # ホスト名の場合は解決せず許可（DNS リバインディングは運用側で対処）
        pass
    return True


def _apply_config_overrides(config_dict: Optional[dict]) -> dict:
    """Apply configuration overrides for a task and return original values for restoration.

    This replaces the deprecated ``ProjectContext`` usage with direct manipulation of the
    global ``Settings`` instance from ``config.settings``. Only keys explicitly listed in
    ``_CONFIG_OVERRIDE_KEYS`` are honored.
    """
    """Apply configuration overrides and return a dict of (key, original_value) for restoration.
    Returns a dict mapping key to original_value (or _NO_VALUE if key did not exist).
    Caller is responsible for restoring the original values after use.
    """
    if not config_dict:
        return {}
    try:
        from config.settings import get_settings
        overrides = {}
        settings_obj = get_settings()
        for key in _CONFIG_OVERRIDE_KEYS:
            if key in config_dict and config_dict[key] not in (None, ""):
                if key == "openai_base_url" and not _is_safe_base_url(str(config_dict[key])):
                    logger.warning(
                        f"Rejected unsafe openai_base_url override: {config_dict[key]}"
                    )
                    continue
                # Get the original value
                original_value = getattr(settings_obj, key, _NO_VALUE)
                overrides[key] = original_value
                # Apply the override directly on the settings object
                setattr(settings_obj, key, config_dict[key])
        return overrides
    except (AttributeError, TypeError, KeyError, ValueError) as e:
        log_exception(logger, "Failed to apply config overrides", e)
        return {}


@huey.periodic_task(crontab(minute='*'))
def process_outbox_events():
    """Huey periodic task for processing Outbox events."""
    logger.info("Running outbox processor task...")
    import asyncio
    try:
        asyncio.run(_process_outbox_events_async())
    except (RuntimeError, asyncio.CancelledError) as e:
        log_exception(logger, "Failed to process outbox events", e)


async def _process_outbox_events_async():
    container = get_container()
    db = container.db()
    uow = UnitOfWork(db=db)

    async with uow:
        events = await uow.get_pending_outbox_events()
        for event in events:
            try:
                await uow.mark_outbox_event_processed(event.id)
            except (ValueError, RuntimeError, KeyError) as e:
                log_exception(logger, f"Failed to process outbox event {event.id}", e)


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
            # Apply config overrides and get original values for restoration
            overrides = _apply_config_overrides(config_dict)

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

        except (ValueError, RuntimeError, KeyError, TypeError) as e:
            log_exception(logger, "Workflow error", e)
            state.is_running = False
            state.error = str(e)
            state._save_to_db()
        finally:
            # Restore config overrides to original values
            from config.settings import get_settings
            settings = get_settings()
            for key, original_value in overrides.items():
                if original_value is _NO_VALUE:
                    # Key did not exist originally; remove the attribute if present
                    if hasattr(settings, key):
                        delattr(settings, key)
                else:
                    setattr(settings, key, original_value)

    try:
        asyncio.run(_run())
    except (RuntimeError, asyncio.CancelledError) as e:
        log_exception(logger, "Task execution failed", e)


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

# Task for overriding affinity (narrative endpoint)
@huey.task(retries=3, retry_delay=5)
@with_trace_context
def run_override_affinity_task(task_id: str, book_id: int, branch_id: int, req_data: dict, api_key: str):
    """Background task to apply affinity overrides and broadcast SSE."""
    import asyncio

    from src.backend.background import BackgroundReporter, ProgressState
    from src.backend.database import UnitOfWork
    from src.backend.sse_manager import get_sse_manager
    from src.backend.workflows.narrative_state import NarrativeState
    from src.schemas.ux_schemas import AffinityData

    state = ProgressState(is_running=True, task_id=task_id, repo=None)
    BackgroundReporter(state)

    async def _run():
        try:
            async with UnitOfWork(AppContainer.db()) as uow:
                raw_data = await uow.misc.load_narrative(book_id, branch_id)
                if raw_data:
                    narrative_state = NarrativeState.from_dict(raw_data)
                else:
                    narrative_state = NarrativeState(book_id=book_id, branch_id=branch_id)

                cname = req_data.get("character_name")
                existing = narrative_state.affinity_map.get(cname)
                if not isinstance(existing, AffinityData):
                    if isinstance(existing, dict):
                        existing_copy = dict(existing)
                        existing_copy.setdefault("character_name", cname)
                        try:
                            existing = AffinityData(**existing_copy)
                        except (TypeError, ValueError):
                            existing = AffinityData(character_name=cname)
                    elif isinstance(existing, (int, float)):
                        existing = AffinityData(character_name=cname, affinity_score=float(existing))
                    else:
                        existing = AffinityData(character_name=cname)

                for field in ["affinity_score", "trust_score", "dependency_score", "wariness_score", "current_mood"]:
                    val = req_data.get(field)
                    if val is not None:
                        setattr(existing, field, val)
                existing.recent_change = 0.0

                narrative_state.affinity_map[cname] = existing
                await uow.misc.save_narrative(book_id, branch_id, narrative_state.to_dict())

            sse = get_sse_manager()
            await sse.broadcast(
                "affinity_overridden",
                {
                    "book_id": book_id,
                    "branch_id": branch_id,
                    "character_name": cname,
                    "affinity_data": existing.model_dump(),
                    "message": f"{cname} の好感度・心理状態が手動更新されました (好意:{existing.affinity_score}, 状態:{existing.current_mood})",
                },
            )

            state.result_data = {"status": "success", "character_name": cname, "affinity_data": existing.model_dump()}
            state.is_running = False
            state.message = "Affinity override completed"
            state._save_to_db()
        except (ValueError, RuntimeError, KeyError, TypeError) as e:
            log_exception(logger, "Affinity override task failed", e)
            state.is_running = False
            state.error = str(e)
            state._save_to_db()

    try:
        asyncio.run(_run())
    except (RuntimeError, asyncio.CancelledError) as e:
        log_exception(logger, "Task execution failed", e)


# Task for rebuilding plot with foreshadows (narrative endpoint)
@huey.task(retries=3, retry_delay=5)
@with_trace_context
def run_rebuild_plot_task(task_id: str, book_id: int, branch_id: int, req_data: dict, api_key: str):
    """Background task to rebuild plot using foreshadow data and broadcast SSE."""
    import asyncio

    from src.backend.background import BackgroundReporter, ProgressState
    from src.backend.database import UnitOfWork
    from src.backend.sse_manager import get_sse_manager
    from src.backend.workflows.graphs.plot_graph import compile_plot_graph

    state = ProgressState(is_running=True, task_id=task_id, repo=None)
    BackgroundReporter(state)

    async def _run():
        try:
            from novel_50ep.foreshadow_manager import ForeshadowManager
            fm = ForeshadowManager()
            try:
                from src.prototype.foreshadow_adapter import PersistentForeshadowManager
                pfm = PersistentForeshadowManager(csv_path=fm.csv_path, cliffs_path=fm.cliffs_path)
                async with UnitOfWork(AppContainer.db()) as uow:
                    db_data = await pfm.load_persistent(book_id, branch_id, repo=uow.misc)
                    if db_data:
                        fm.foreshadows = db_data
            except (ImportError, AttributeError, RuntimeError):
                # PersistentForeshadowManager が利用不可、または読み込み失敗時は無視
                pass

            unresolved = fm.get_unresolved_foreshadows()
            stale = fm.get_stale_foreshadows(current_ep=req_data.get("current_ep", 1), threshold=3)

            foreshadow_list = []
            for s in stale:
                foreshadow_list.append({
                    "ep": s.ep if hasattr(s, "ep") else s.get("ep"),
                    "text": f'【最優先放置伏線】{s.text if hasattr(s, "text") else s.get("text")}',
                })
            for u in unresolved:
                if u not in stale:
                    foreshadow_list.append({
                        "ep": u.ep if hasattr(u, "ep") else u.get("ep"),
                        "text": u.text if hasattr(u, "text") else u.get("text"),
                    })

            app = compile_plot_graph()
            target_eps = req_data.get("target_episodes") or 10
            extra_inst = req_data.get("user_instructions") or ""
            if stale:
                extra_inst += f" ※長期未回収となっている伏線（{len(stale)}件）を必ず序盤の話数で回収・進展させてください。"

            initial_state = {
                "book_id": book_id,
                "branch_id": branch_id,
                "genre": req_data.get("genre"),
                "theme": req_data.get("theme"),
                "target_episodes": target_eps,
                "user_instructions": extra_inst,
                "unresolved_foreshadows": foreshadow_list,
                "max_iterations": 2,
            }

            result = await app.ainvoke(initial_state)

            sse = get_sse_manager()
            await sse.broadcast(
                "plot_rebuilt",
                {
                    "book_id": book_id,
                    "branch_id": branch_id,
                    "current_ep": req_data.get("current_ep"),
                    "plots_count": len(result.get("parsed_plots", [])),
                    "resolved_foreshadows_assigned": sum(
                        len(p.get("assigned_foreshadows", []))
                        for p in result.get("parsed_plots", [])
                        if isinstance(p, dict)
                    ),
                    "message": f"第{req_data.get('current_ep')}話以降のプロットを伏線回収優先で再構成しました。",
                },
            )

            state.result_data = result
            state.is_running = False
            state.message = "Plot rebuild completed"
            state._save_to_db()
        except (ValueError, RuntimeError, KeyError, TypeError) as e:
            log_exception(logger, "Plot rebuild task failed", e)
            state.is_running = False
            state.error = str(e)
            state._save_to_db()

    try:
        asyncio.run(_run())
    except (RuntimeError, asyncio.CancelledError) as e:
        log_exception(logger, "Task execution failed", e)

@huey.task(retries=3, retry_delay=5)
@with_trace_context
def async_score_narrative_metrics(book_id: int, branch_id: int, ep_num: int, trace_id: Optional[str] = None):
    """エピソードのスコアリングをバックグラウンドで実行するタスク"""
    import asyncio

    from src.backend.database.repositories.narrative_metrics_repo import NarrativeMetricRepository
    from src.services.narrative_scoring_service import NarrativeScoringService

    async def _run():
        try:
            db = AppContainer.db()
            async with db.get_session() as session:
                auditor = AppContainer.auditor()
                metrics_repo = NarrativeMetricRepository(session)
                service = NarrativeScoringService(session, auditor, metrics_repo)
                success = await service.rescore_episode(book_id, branch_id, ep_num)
                logger.info(f"Background scoring for Ep.{ep_num} finished. Success: {success}")
                return success
        except (ValueError, RuntimeError, KeyError, TypeError, AttributeError) as e:
            log_exception(logger, f"Error in async_score_narrative_metrics for Ep.{ep_num}", e)
            return False

    return asyncio.run(_run())


@huey.task(retries=3, retry_delay=5)
@with_trace_context
def enqueue_audit_after_write(book_id: int, write_from: int, write_to: int, trace_id: Optional[str] = None):
    """執筆完了後の論理監査 (Shadow Mode) をバックグラウンドで実行するタスク。"""
    import asyncio

    async def _run():
        try:
            db = AppContainer.db()
            async with db.get_session() as session:
                auditor = AppContainer.auditor()
                for ep_num in range(write_from, write_to + 1):
                    await auditor.audit_episode(session, book_id, ep_num)
                logger.info(
                    f"Shadow audit finished for book_id={book_id}, ep{write_from}-ep{write_to}"
                )
        except (ValueError, RuntimeError, KeyError, TypeError, AttributeError) as e:
            log_exception(logger, f"Error in enqueue_audit_after_write for book_id={book_id}", e)

    return asyncio.run(_run())


@huey.task(retries=3, retry_delay=5)
@with_trace_context
def execute_easy_mode_generation(task_id: str, api_key: str, genre: str, keywords: str, archetype_key: str, target_eps: int, initial_limit: int, word_count: int, concept: str, tone_vibe: float, style_key: Optional[str], enable_erotic: bool, erotic_intensity: int, trace_id: Optional[str] = None):
    """かんたんモード全自動生成をバックグラウンドで実行するタスク"""
    import asyncio

    from src.backend.background import BackgroundReporter, ProgressState
    from src.backend.workflows.full_auto_workflow import FullAutoWorkflow

    state = ProgressState(is_running=True, task_id=task_id, repo=None)
    reporter = BackgroundReporter(state)

    async def _run():
        try:
            container = AppContainer(
                api_key=api_key,
                db=AppContainer.db(),
            )
            services = _build_service_dict(container)
            state.repo = services["repo"]

            workflow = FullAutoWorkflow(**services)
            result = await workflow.execute(
                reporter,
                genre=genre,
                keywords=keywords,
                archetype_key=archetype_key,
                target_eps=target_eps,
                initial_limit=initial_limit,
                word_count=word_count,
                concept=concept,
                tone_vibe=tone_vibe,
                style_key=style_key,
                enable_erotic=enable_erotic,
                erotic_intensity=erotic_intensity,
            )

            state.is_running = False
            state.message = "生成完了"
            state.result_data = result
            state._save_to_db()

            logger.info(f"Easy mode pipeline completed: {task_id}")

        except (ValueError, RuntimeError, KeyError, TypeError) as e:
            log_exception(logger, "Easy mode pipeline failed", e)
            state.is_running = False
            state.error = str(e)
            state._save_to_db()

    try:
        asyncio.run(_run())
    except (RuntimeError, asyncio.CancelledError) as e:
        log_exception(logger, "Task execution failed", e)


@huey.task(retries=3, retry_delay=5)
@with_trace_context
def run_commercial_pipeline_task(task_id: str, series_config: dict, samples: list, platforms: list, api_key: str, trace_id: Optional[str] = None):
    """商用化パイプラインをバックグラウンドで実行するタスク"""
    import asyncio
    import logging

    from src.backend.background import BackgroundReporter, ProgressState
    from src.backend.workflows.commercial_pipeline import CommercialPipeline

    # Use the module-level logger (or create a local one)
    logger = logging.getLogger('huey')

    state = ProgressState(is_running=True, task_id=task_id, repo=None)
    BackgroundReporter(state)

    async def _run():
        try:
            # Apply config overrides if needed (the endpoint does not apply overrides, but we can support them if passed via a config_dict)
            # For now, we assume the config is already final.
            pipeline = CommercialPipeline()
            result = await pipeline.run(
                series_config=series_config,
                samples=samples,
                platforms=platforms
            )
            state.result_data = result
            state.is_running = False
            state.message = "商用化パイプラインが完了しました。"
            state._save_to_db()
        except (ValueError, RuntimeError, KeyError, TypeError) as e:
            log_exception(logger, "Commercial pipeline error", e)
            state.is_running = False
            state.error = str(e)
            state._save_to_db()

    try:
        asyncio.run(_run())
    except (RuntimeError, asyncio.CancelledError) as e:
        log_exception(logger, "Task execution failed", e)
