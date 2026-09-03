"""Health check payload builder and basic in-memory metrics."""
from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

logger = logging.getLogger(__name__)


class _Metrics:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {
            "tasks_enqueued": 0,
            "tasks_completed": 0,
            "tasks_failed": 0,
            "exports_attempted": 0,
            "exports_succeeded": 0,
            "health_checks": 0,
            "streaming_disconnects": 0,
            "multimedia_requests_total": 0,
            "multimedia_errors_total": 0,
        }

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            if name not in self._counters:
                self._counters[name] = 0
            self._counters[name] += amount

    def get(self, name: str) -> int:
        with self._lock:
            return self._counters.get(name, 0)

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counters)

    def reset(self) -> None:
        self.reset_for_testing()

    def reset_for_testing(self) -> None:
        with self._lock:
            for k in self._counters:
                self._counters[k] = 0


metrics = _Metrics()


async def check_database(timeout: float = 5.0) -> dict[str, Any]:
    """SQLite / PostgreSQL への actual ping を実行する。"""
    try:
        from sqlalchemy import text

        from src.backend.config import settings
        from src.backend.database.core import DatabaseManager, get_db_manager

        mgr: DatabaseManager = get_db_manager()
        async with asyncio.timeout(timeout):
            async with mgr.get_session() as session:
                await session.execute(text("SELECT 1"))
        db_type = "postgresql" if "postgresql" in settings.DATABASE_URL else "sqlite"
        return {"status": "ok", "type": db_type}
    except asyncio.TimeoutError:
        logger.warning("[health] Database ping timed out after %ss", timeout)
        return {"status": "error", "code": "DB_TIMEOUT"}
    except Exception as e:
        logger.warning("[health] Database health check failed: %s", e)
        return {"status": "error", "code": "DB_UNAVAILABLE"}


async def check_huey(timeout: float = 3.0) -> dict[str, Any]:
    """Huey ワーカー / Redis / SQLite キューの生存確認を行う。"""
    try:
        from huey import RedisHuey

        from src.backend.tasks.huey import huey

        def _ping() -> bool:
            if isinstance(huey, RedisHuey):
                return bool(huey.storage.conn.ping())
            if hasattr(huey, "ping"):
                return bool(huey.ping())
            return True

        async with asyncio.timeout(timeout):
            result = await asyncio.to_thread(_ping)
        if result:
            backend_name = "redis" if isinstance(huey, RedisHuey) else "sqlite"
            return {"status": "ok", "backend": backend_name}
        return {"status": "error", "code": "HUEY_NO_RESPONSE"}
    except asyncio.TimeoutError:
        logger.warning("[health] Huey ping timed out after %ss", timeout)
        return {"status": "error", "code": "HUEY_TIMEOUT"}
    except Exception as e:
        logger.warning("[health] Huey health check failed: %s", e)
        return {"status": "error", "code": "HUEY_DOWN"}


async def build_health_payload() -> dict[str, Any]:
    """全コンポーネントのヘルスチェックを実行し_payload を構築する。"""
    metrics.increment("health_checks")
    db_status, huey_status = await asyncio.gather(
        check_database(),
        check_huey(),
    )

    all_ok = db_status.get("status") == "ok" and huey_status.get("status") == "ok"
    overall_status = "ok" if all_ok else "degraded"

    return {
        "status": overall_status,
        "database": db_status,
        "huey": huey_status,
        "components": {
            "database": db_status,
            "queue": huey_status,
        },
        "metrics": metrics.snapshot(),
    }
