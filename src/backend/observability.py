"""オブザーバビリティ支援モジュール (Phase 5: Step 55-58).

- 軽量なメトリクスカウンタ (in-memory, 依存ライブラリ不要)
- DB 接続確認
- Huey (sqlite/redis) 生存確認

外部依存 (Prometheus 等) を持たず、FastAPI lifespan / ヘルスチェック
エンドポイントから参照できるプロセスローカルのメトリクスを提供する。
"""

from __future__ import annotations

import logging
import threading
from typing import Any

from src.backend import database

logger = logging.getLogger(__name__)


class _Metrics:
    """プロセス内で基本カウンタを保持するスレッドセーフなメトリクスレジストリ。

    外部ストア不要の最小実装であり、``/metrics`` 系エンドポイントから
    参照される。本格運用では Prometheus 等への置換を想定 (拡張ポイント)。
    """

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
        """指定したカウンタを ``amount`` だけ増やす (未定義名は無視)。"""
        with self._lock:
            if name in self._counters:
                self._counters[name] += amount

    def snapshot(self) -> dict[str, int]:
        """現在のカウンタのコピーを返す。"""
        with self._lock:
            return dict(self._counters)

    def reset(self) -> None:
        """全カウンタを 0 に戻す (テスト用途)。"""
        with self._lock:
            for key in self._counters:
                self._counters[key] = 0


# モジュール単一インスタンス (プロセス内で共有)
metrics = _Metrics()


def check_database() -> dict[str, Any]:
    """DB エンジンに対する SELECT 1 を実行し接続性を確認する。

    Returns:
        ``{"status": "ok", "latency_ms": <float>}`` または
        ``{"status": "error", "error": <str>}``。
    """
    import time

    from sqlalchemy import text

    started = time.perf_counter()
    try:
        with database.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        latency_ms = (time.perf_counter() - started) * 1000.0
        return {"status": "ok", "latency_ms": round(latency_ms, 3)}
    except Exception as exc:  # noqa: BLE001 - 健監視なので広域 catch
        logger.warning("DB health check failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def check_huey() -> dict[str, Any]:
    """Huey バックエンドの生存確認 (軽量 ping)。

    SqliteHuey / RedisHuey ともに ``len(huey)`` 等の基本操作で例外が
    出なければ「到達可能」と判定する。
    """
    try:
        from src.backend.tasks.huey import huey

        # huey は ``__len__`` を実装する (キュー件数参照)。
        # 実行中に例外が上がれば backends 不達とみなす。
        _ = len(huey)
        return {
            "status": "ok",
            "backend": type(huey).__name__,
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("Huey health check failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def build_health_payload() -> dict[str, Any]:
    """``/health`` エンドポイント用の総合ペイロードを構築する。

    各サブチェック (DB/Huey) の結果を含め、全体 ``status`` を
    ``ok`` (全 ok) / ``degraded`` (いずれか error) / ``ok`` で決定する。
    """
    metrics.increment("health_checks")

    db = check_database()
    queue = check_huey()

    statuses = [db["status"], queue["status"]]
    overall = "ok" if all(s == "ok" for s in statuses) else "degraded"
    return {
        "status": overall,
        "components": {
            "database": db,
            "queue": queue,
        },
        "metrics": metrics.snapshot(),
    }


__all__: list[str] = [
    "metrics",
    "check_database",
    "check_huey",
    "build_health_payload",
]
