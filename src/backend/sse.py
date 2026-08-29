import asyncio
import json
import logging
from typing import AsyncGenerator

from fastapi import Request

from src.backend.redis_util import get_async_redis_client, get_redis_client

logger = logging.getLogger(__name__)


async def task_event_generator(task_id: str, request: Request, last_event_id: str | None = None) -> AsyncGenerator[str, None]:
    """
    Server-Sent Events (SSE) 用のタスク進捗イベントジェネレータ。
    1. Redisが利用可能な場合: Redis Pub/Sub を使ってプッシュ配信。
    2. Redisが利用不可の場合: 1秒ポーリングでデータベースから状態を読み出すフォールバック。
    """
    get_redis_client()

    async_redis = get_async_redis_client()
    if async_redis is not None:
        try:
            # Initial task state (may be in Redis or DB fallback)
            initial_state = await async_redis.get(f"task_status:{task_id}")
            if not initial_state:
                # Fallback to DB if not present in Redis
                from sqlalchemy import select

                from src.backend.database.models import InternalState
                from src.core.container import AppContainer
                db = AppContainer.db()
                try:
                    async with db.get_session() as session:
                        stmt = select(InternalState).where(
                            InternalState.key == f"task_status:{task_id}"
                        )
                        result = await session.execute(stmt)
                        row = result.scalar_one_or_none()
                        if row:
                            initial_state = row.value
                except Exception as db_err:
                    logger.error(f"[SSE] DB check failed for task {task_id}: {db_err}")

            if initial_state:
                state_json = initial_state.decode('utf-8') if isinstance(initial_state, bytes) else initial_state
                state_data = json.loads(state_json)
                event_id = state_data.get("event_id", 0)
                try:
                    last_event_id_int = int(last_event_id) if last_event_id is not None else -1
                except ValueError:
                    last_event_id_int = -1
                if last_event_id is None or event_id > last_event_id_int:
                    yield f"id: {event_id}\n" + f"data: {state_json}\n\n"
                if not state_data.get("is_running", True):
                    return
            else:
                err_state = {"is_running": False, "message": "タスクが見つかりません", "logs": []}
                yield f"data: {json.dumps(err_state, ensure_ascii=False)}\n\n"
                return

            pubsub = async_redis.pubsub()
            await pubsub.subscribe(f"task_events:{task_id}")
            logger.info(f"[SSE] Subscribed to async Redis channel task_events:{task_id}")

            while True:
                if await request.is_disconnected():
                    break
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message["type"] == "message":
                    data = message["data"]
                    decoded_data = data.decode("utf-8") if isinstance(data, bytes) else data
                    state = json.loads(decoded_data)
                    event_id = state.get("event_id", 0)
                    yield f"id: {event_id}\n" + f"data: {decoded_data}\n\n"
                    if not state.get("is_running", True):
                        logger.info(f"[SSE] Task {task_id} completed. Closing async Redis stream.")
                        break
                await asyncio.sleep(0.1)
            await pubsub.unsubscribe(f"task_events:{task_id}")
            await pubsub.close()
            return
        except Exception as e:
            logger.error(f"[SSE] Async Redis subscription failed ({e}). Falling back to SQLite polling.")

    # SQLiteポーリングフォールバック
    async for event in _sqlite_polling_fallback(task_id, last_event_id=last_event_id, request=request):
        yield event


async def _sqlite_polling_fallback(task_id: str, request: Request, last_event_id: str | None = None) -> AsyncGenerator[str, None]:
    """
    Redis未接続時のデータベース（SQLite/PostgreSQL）1秒ポーリングによるフォールバック。
    """
    from sqlalchemy import select

    from src.backend.database.models import InternalState
    from src.core.container import AppContainer

    db = AppContainer.db()
    logger.info(f"[SSE] Starting database polling fallback for task {task_id}")

    # 最初のチェックでタスクが見つからない場合は終了する
    try:
        async with db.get_session() as session:
            stmt = select(InternalState).where(InternalState.key == f"task_status:{task_id}")
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if not row:
                err_state = {"is_running": False, "message": "タスクが見つかりません", "logs": [], "event_id": 0}
                yield "id: 0\n" + f"data: {json.dumps(err_state, ensure_ascii=False)}\n\n"
                return
    except Exception as e:
        logger.error(f"[SSE] Database initial task check error: {e}")
        return

    last_val = None
    while True:
        if await request.is_disconnected():
            break
        try:
            async with db.get_session() as session:
                stmt = select(InternalState).where(InternalState.key == f"task_status:{task_id}")
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
                if row:
                    val = row.value
                    # 重複したイベントの送信を抑制
                    if val != last_val:
                        state = json.loads(val)
                        event_id = state.get("event_id", 0)
                        # Filter based on last_event_id
                        try:
                            last_event_id_int = int(last_event_id) if last_event_id is not None else -1
                        except ValueError:
                            last_event_id_int = -1
                        if last_event_id is None or event_id > last_event_id_int:
                            yield f"id: {event_id}\n" + f"data: {val}\n\n"
                        last_val = val

                        if not state.get("is_running", True):
                            logger.info(
                                f"[SSE] Task {task_id} completed. Closing database polling."
                            )
                            break
        except Exception as e:
            logger.error(f"[SSE] Database polling error: {e}")

        await asyncio.sleep(1.0)
