from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
import json
import time
from typing import Any, Dict

from config.container import Container
from src.backend.redis_util import get_redis_client
from src.backend.sse import task_event_generator
from sqlalchemy import select
from src.backend.database.models import InternalState
from src.core.exceptions import NotFoundError
from src.backend.auth import require_api_key

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

@router.get("/{task_id}/status")
async def get_task_status(task_id: str):
    redis_client = get_redis_client()
    if redis_client is not None:
        try:
            val = redis_client.get(f"task_status:{task_id}")
            if val:
                return json.loads(val)
        except Exception:
            pass

    db = Container.db()
    async with db.get_session() as session:
        stmt = select(InternalState).where(InternalState.key == f"task_status:{task_id}")
        result = await session.execute(stmt)
        row = result.scalar_one_or_none()
    if not row:
        return {"is_running": False, "message": "タスクが見つかりません", "logs": []}
    return json.loads(row.value)

@router.get("/{task_id}/stream")
async def stream_task_status(task_id: str):
    return StreamingResponse(
        task_event_generator(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable Nginx buffering
        }
    )

@router.post("/{task_id}/stop")
async def stop_task(task_id: str, api_key: str = Depends(require_api_key)):
    # Retrieve current task status, set stop event
    redis_client = get_redis_client()
    state_dict = None
    if redis_client is not None:
        try:
            val = redis_client.get(f"task_status:{task_id}")
            if val:
                state_dict = json.loads(val)
        except Exception:
            pass

    db = Container.db()
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
    state_dict["logs"].append(f"[{time.strftime('%H:%M:%S')}] 🛑 ユーザーにより停止命令が出されました。")

    state_json = json.dumps(state_dict)
    if redis_client is not None:
        try:
            redis_client.set(f"task_status:{task_id}", state_json, ex=86400)
            return {"message": "Stop request registered via Redis"}
        except Exception:
            pass

    await db.save_internal_state(f"task_status:{task_id}", state_json, time.strftime('%Y-%m-%d %H:%M:%S'))
    return {"message": "Stop request registered"}
