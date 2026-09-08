"""Huey タスクキュー設定。環境変数で sqlite/redis を切り替える。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from huey import RedisHuey, SqliteHuey

from src.backend.config import settings

logger = logging.getLogger(__name__)

# Step 37: バックエンド初期化と耐障害設定
if settings.HUEY_BACKEND == "redis":
    try:
        huey = RedisHuey(
            "autonovel",
            url=settings.REDIS_URL,
            results=True,
            result_store=True,
        )
    except Exception as e:
        logger.warning("Failed to initialize RedisHuey, falling back to SqliteHuey: %s", e)
        sqlite_path = Path(settings.HUEY_SQLITE_PATH)
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        huey = SqliteHuey("autonovel", filename=str(sqlite_path), results=True)
else:
    sqlite_path = Path(settings.HUEY_SQLITE_PATH)
    sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    huey = SqliteHuey(
        "autonovel",
        filename=str(sqlite_path),
        results=True,
    )

# ワーカー上でキュー経由で実行（immediate=False）
huey.immediate = False


# Step 38 & 39 & 40 & 44: 分散実行用 Huey タスク（エラーハンドリング強化）
@huey.task(retries=2, retry_delay=5)
def execute_agent_node_task(
    node_name: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Huey 分散ワーカー上で単一エージェントノードまたはタスクを実行 (Step 39, 40, 44)"""
    import asyncio
    logger.info("Huey worker executing task for node: %s", node_name)

    async def _run():
        try:
            if node_name == "ping":
                return {"status": "pong", "payload": payload}
            elif node_name == "raise_error":
                raise RuntimeError(payload.get("error_msg", "Forced test failure"))
            elif node_name == "social_process":
                from src.agents.social.manager import SocialInteractionManager
                manager = SocialInteractionManager()
                return await manager.process_scene_async(
                    book_id=payload.get("book_id", 1),
                    ep_num=payload.get("ep_num", 1),
                    scene_text=payload.get("scene_text", ""),
                    characters=payload.get("characters"),
                )
            else:
                return {"node": node_name, "status": "completed", "input_keys": list(payload.keys())}
        except Exception as e:
            logger.error("Error executing task for node %s on Huey worker: %s", node_name, e, exc_info=True)
            return {
                "node": node_name,
                "status": "failed",
                "error": str(e),
                "payload": payload,
            }

    return asyncio.run(_run())


# Step 43: Hueyタスク実行結果の非同期取得ラッパー
async def async_wait_huey_result(
    result: Any,
    timeout: float = 60.0,
    poll_interval: float = 0.05,
) -> Any:
    """FastAPI/asyncio イベントループをブロックせずに Huey 結果を非同期ポーリング (Step 43)"""
    import asyncio
    import time

    if not hasattr(result, "get"):
        return result

    start_time = time.monotonic()
    while time.monotonic() - start_time < timeout:
        # non-blocking で取得試行 (None または 未解決値の確認)
        val = result.get(blocking=False)
        if val is not None:
            return val
        await asyncio.sleep(poll_interval)

    raise TimeoutError(f"Huey task result timed out after {timeout:.1f}s")


# Step 42: キューの健全性チェック
def check_huey_health() -> dict[str, Any]:
    """Huey タスクキューの接続状態・保留タスク数をチェック (Step 42)"""
    try:
        backend_type = "redis" if isinstance(huey, RedisHuey) else "sqlite"
        pending_count = len(huey)

        return {
            "status": "healthy",
            "backend": backend_type,
            "pending_tasks": pending_count,
            "immediate_mode": huey.immediate,
        }
    except Exception as e:
        logger.error("Huey health check failed: %s", e)
        return {
            "status": "unhealthy",
            "error": str(e),
        }


# ワーカー側でタスクを認識するためにここでインポートしておく
import src.backend.tasks  # noqa
import src.backend.tasks.generation_tasks  # noqa

__all__: list[str] = [
    "huey",
    "execute_agent_node_task",
    "async_wait_huey_result",
    "check_huey_health",
    "logger",
]
