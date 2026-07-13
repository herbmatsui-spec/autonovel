import asyncio
import json
import logging
from typing import AsyncGenerator

from src.backend.redis_util import get_redis_client

logger = logging.getLogger(__name__)

async def task_event_generator(task_id: str) -> AsyncGenerator[str, None]:
    """
    Server-Sent Events (SSE) 用のタスク進捗イベントジェネレータ。
    1. Redisが利用可能な場合: Redis Pub/Sub を使ってプッシュ配信。
    2. Redisが利用不可の場合: 1秒ポーリングでデータベースから状態を読み出すフォールバック。
    """
    redis_client = get_redis_client()

    if redis_client is not None:
        try:
            # 既に保存されている現在のステータスを最初に送信
            initial_state = redis_client.get(f"task_status:{task_id}")
            if not initial_state:
                from sqlalchemy import select

                from config.container import Container
                from src.backend.database.models import InternalState
                db = Container.db()
                try:
                    async with db.get_session() as session:
                        stmt = select(InternalState).where(InternalState.key == f"task_status:{task_id}")
                        result = await session.execute(stmt)
                        row = result.scalar_one_or_none()
                        if row:
                            initial_state = row.value
                except Exception as db_err:
                    logger.error(f"[SSE] DB check failed for task {task_id}: {db_err}")

            if initial_state:
                yield f"data: {initial_state.decode('utf-8') if isinstance(initial_state, bytes) else initial_state}\n\n"
                state_data = json.loads(initial_state)
                if not state_data.get("is_running", True):
                    # 既に実行中でないなら終了
                    return
            else:
                err_state = {"is_running": False, "message": "タスクが見つかりません", "logs": []}
                yield f"data: {json.dumps(err_state, ensure_ascii=False)}\n\n"
                return

            pubsub = redis_client.pubsub()
            pubsub.subscribe(f"task_events:{task_id}")
            logger.info(f"[SSE] Subscribed to Redis channel task_events:{task_id}")

            try:
                while True:
                    # Redisの非ブロッキング取得
                    message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message and message["type"] == "message":
                        data = message["data"]
                        decoded_data = data.decode("utf-8") if isinstance(data, bytes) else data
                        yield f"data: {decoded_data}\n\n"

                        # 進捗イベントの終了判定
                        state = json.loads(decoded_data)
                        if not state.get("is_running", True):
                            logger.info(f"[SSE] Task {task_id} completed. Closing Redis stream.")
                            break
                    await asyncio.sleep(0.1)
            finally:
                pubsub.unsubscribe(f"task_events:{task_id}")
                pubsub.close()
            return
        except Exception as e:
            logger.error(f"[SSE] Redis subscription failed ({e}). Falling back to SQLite polling.")

    # SQLiteポーリングフォールバック
    async for event in _sqlite_polling_fallback(task_id):
        yield event

async def _sqlite_polling_fallback(task_id: str) -> AsyncGenerator[str, None]:
    """
    Redis未接続時のデータベース（SQLite/PostgreSQL）1秒ポーリングによるフォールバック。
    """
    from sqlalchemy import select

    from config.container import Container
    from src.backend.database.models import InternalState

    db = Container.db()
    logger.info(f"[SSE] Starting database polling fallback for task {task_id}")

    # 最初のチェックでタスクが見つからない場合は終了する
    try:
        async with db.get_session() as session:
            stmt = select(InternalState).where(InternalState.key == f"task_status:{task_id}")
            result = await session.execute(stmt)
            row = result.scalar_one_or_none()
            if not row:
                err_state = {"is_running": False, "message": "タスクが見つかりません", "logs": []}
                yield f"data: {json.dumps(err_state, ensure_ascii=False)}\n\n"
                return
    except Exception as e:
        logger.error(f"[SSE] Database initial task check error: {e}")
        return

    last_val = None
    while True:
        try:
            async with db.get_session() as session:
                stmt = select(InternalState).where(InternalState.key == f"task_status:{task_id}")
                result = await session.execute(stmt)
                row = result.scalar_one_or_none()
                if row:
                    val = row.value
                    # 重複したイベントの送信を抑制
                    if val != last_val:
                        yield f"data: {val}\n\n"
                        last_val = val

                        state = json.loads(val)
                        if not state.get("is_running", True):
                            logger.info(f"[SSE] Task {task_id} completed. Closing database polling.")
                            break
        except Exception as e:
            logger.error(f"[SSE] Database polling error: {e}")

        await asyncio.sleep(1.0)


