import json
import logging
import time

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from src.backend.auth import require_api_key
from src.backend.database.models import InternalState, TaskWALLogModel
from src.backend.redis_util import get_async_redis_client
from src.backend.sse import task_event_generator
from src.backend.tasks.worker_recovery import WorkerRecoveryManager, RecoveryConfig
from src.core.container import AppContainer
from src.core.exceptions import NotFoundError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("/{task_id}/status")
async def get_task_status(task_id: str):
    redis_client = await get_async_redis_client()
    if redis_client is not None:
        try:
            val = await redis_client.get(f"task_status:{task_id}")
            if val:
                return json.loads(val)
        except Exception as exc:
            # Redis 取得失敗は DB フォールバックへ進む想定だが、原因を追跡できるようログは残す
            logger.warning(
                "Redis task_status 取得失敗、DB にフォールバックします: %s", exc, exc_info=True
            )

    db = AppContainer.db()
    async with db.get_session() as session:
        stmt = select(InternalState).where(InternalState.key == f"task_status:{task_id}")
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
    if not row:
        return {"is_running": False, "message": "タスクが見つかりません", "logs": []}
    return json.loads(row.value)


@router.get("/dag/{dag_id}")
async def get_dag_status(dag_id: str):
    """Step 57: Get DAG workflow status, progress, and node execution states."""
    from src.backend.tasks.dag_persistence import FileSystemDAGPersistence
    from src.backend.tasks.dag_scheduler import DAGScheduler

    persistence = FileSystemDAGPersistence()
    checkpoints = persistence.list_checkpoints(dag_id)
    if checkpoints:
        latest_cp = checkpoints[-1]
        graph = persistence.load_checkpoint(latest_cp)
        if graph:
            scheduler = DAGScheduler(persistence=persistence)
            summary = scheduler.get_execution_summary(graph)
            summary["latest_checkpoint"] = latest_cp
            return summary

    # Check Redis
    redis_client = await get_async_redis_client()
    if redis_client is not None:
        try:
            val = await redis_client.get(f"dag_status:{dag_id}")
            if val:
                return json.loads(val)
        except Exception as exc:
            logger.warning("Redis dag_status error: %s", exc)

    return {
        "dag_id": dag_id,
        "found": False,
        "message": f"DAG workflow '{dag_id}' not found in checkpoints or cache",
    }


@router.get("/{task_id}/stream")
async def stream_task_status(task_id: str):
    return StreamingResponse(
        task_event_generator(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        },
    )


@router.post("/{task_id}/stop")
async def stop_task(task_id: str, api_key: str = Depends(require_api_key)):
    # Retrieve current task status, set stop event
    redis_client = await get_async_redis_client()
    state_dict = None
    if redis_client is not None:
        try:
            val = await redis_client.get(f"task_status:{task_id}")
            if val:
                state_dict = json.loads(val)
        except Exception as exc:
            logger.warning(
                "Redis task_status 取得失敗、DB にフォールバックします: %s", exc, exc_info=True
            )

    db = AppContainer.db()
    if not state_dict:
        async with db.get_session() as session:
            stmt = select(InternalState).where(InternalState.key == f"task_status:{task_id}")
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
        if not row:
            raise NotFoundError("Task not found", resource_type="TaskStatus", resource_id=task_id)
        state_dict = json.loads(row.value)

    state_dict["is_running"] = False
    state_dict["error"] = "ユーザーにより停止されました"
    state_dict["logs"].append(
        f"[{time.strftime('%H:%M:%S')}] 🛑 ユーザーにより停止命令が出されました。"
    )

    state_json = json.dumps(state_dict)
    if redis_client is not None:
        try:
            await redis_client.set(f"task_status:{task_id}", state_json, ex=86400)
            return {"message": "Stop request registered via Redis"}
        except Exception as exc:
            logger.warning(
                "Redis task_status 保存失敗、DB にフォールバックします: %s", exc, exc_info=True
            )

    await db.save_internal_state(
        f"task_status:{task_id}", state_json, time.strftime("%Y-%m-%d %H:%M:%S")
    )
    return {"message": "Stop request registered"}


@router.post("/admin/recover", dependencies=[Depends(require_api_key)])
async def trigger_task_recovery():
    """Step 58: Manual trigger for orphan task detection and recovery.
    
    Scans for zombie tasks (running with stale heartbeat) and resets them to pending
    for re-scheduling. Returns count of recovered tasks.
    """
    db_manager = AppContainer.db()
    recovery_manager = WorkerRecoveryManager(
        db_manager=db_manager,
        config=RecoveryConfig(),
    )
    
    recovered_tasks = await recovery_manager.recover_orphan_tasks()
    
    return {
        "recovered_count": len(recovered_tasks),
        "recovered_task_ids": recovered_tasks,
        "message": f"Recovered {len(recovered_tasks)} orphan tasks" if recovered_tasks else "No orphan tasks found",
    }


@router.get("/admin/recover/zombies")
async def list_zombie_tasks():
    """List current zombie tasks (running with stale heartbeat) without recovering them."""
    db_manager = AppContainer.db()
    recovery_manager = WorkerRecoveryManager(
        db_manager=db_manager,
        config=RecoveryConfig(),
    )
    
    zombies = await recovery_manager.detect_zombie_tasks()
    
    return {
        "zombie_count": len(zombies),
        "zombies": [
            {
                "task_id": z.task_id,
                "dag_id": z.dag_id,
                "node_id": z.node_id,
                "heartbeat_at": z.heartbeat_at.isoformat() if z.heartbeat_at else None,
                "created_at": z.created_at.isoformat() if z.created_at else None,
            }
            for z in zombies
        ],
    }


@router.get("/admin/wal/{dag_id}")
async def get_wal_logs(dag_id: str):
    """Get WAL logs for a specific DAG for debugging."""
    db_manager = AppContainer.db()
    
    async with db_manager.get_session() as session:
        stmt = select(TaskWALLogModel).where(
            TaskWALLogModel.dag_id == dag_id
        ).order_by(TaskWALLogModel.created_at.desc()).limit(100)
        result = await session.execute(stmt)
        logs = result.scalars().all()
    
    return {
        "dag_id": dag_id,
        "logs": [
            {
                "id": log.id,
                "task_id": log.task_id,
                "node_id": log.node_id,
                "state": log.state,
                "input_json": log.input_json,
                "output_json": log.output_json,
                "heartbeat_at": log.heartbeat_at.isoformat() if log.heartbeat_at else None,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
    }
