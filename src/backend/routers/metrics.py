from fastapi import APIRouter

from src.backend.observability.metrics import metrics_endpoint

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def prometheus_metrics():
    """Prometheus 形式でメトリクスを公開"""
    return await metrics_endpoint()


# 既存の huey-sqlite-busy エンドポイントは互換性のため残却、非推奨化
@router.get("/metrics/huey-sqlite-busy", deprecated=True)
async def huey_sqlite_busy_metrics():
    """Deprecated: Use /metrics instead"""
    from src.backend.tasks import huey

    try:
        pending_count = huey.pending_count()
        backend_class = huey.backend.__class__.__name__ if hasattr(huey, "backend") else "unknown"
        return {
            "huey_sqlite_busy_total": pending_count,
            "huey_backend": "sqlite"
            if "Sqlite" in backend_class
            else "redis"
            if "Redis" in backend_class
            else "unknown",
        }
    except Exception:
        return {"huey_sqlite_busy_total": 0, "huey_backend": "unknown"}
