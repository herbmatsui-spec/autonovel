"""Health check payload builder and basic in-memory metrics."""
from __future__ import annotations

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
        }

    def increment(self, name: str, amount: int = 1) -> None:
        with self._lock:
            if name in self._counters:
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


def check_database() -> dict[str, Any]:
    try:
        from src.backend.database.core import DatabaseManager
        return {"status": "ok", "type": "sqlite"}
    except Exception as e:
        logger.warning(f"Database health check failed: {e}")
        return {"status": "error", "error": str(e)}


def check_huey() -> dict[str, Any]:
    try:
        from src.backend.tasks.huey import huey
        return {"status": "ok", "backend": "sqlite"}
    except Exception as e:
        logger.warning(f"Huey health check failed: {e}")
        return {"status": "error", "error": str(e)}


def build_health_payload() -> dict[str, Any]:
    metrics.increment("health_checks")
    db_status = check_database()
    huey_status = check_huey()

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

