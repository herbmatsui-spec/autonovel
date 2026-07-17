from fastapi import APIRouter
from config.container import Container

router = APIRouter(tags=["system"])

@router.get("/health")
async def health_check():
    try:
        db_manager = Container.db()
        async with db_manager.engine.acquire() as conn:
            await conn.execute("SELECT 1")
        db_status = "ok"
    except Exception:
        db_status = "error"

    worker_status = "ok"
    huey_backend = "unknown"
    queue_depth = 0
    try:
        from src.backend.tasks import huey
        # Determine Huey backend type
        if hasattr(huey, 'backend') and hasattr(huey.backend, '__class__'):
            backend_class = huey.backend.__class__.__name__
            if "Redis" in backend_class:
                huey_backend = "redis"
            elif "Sqlite" in backend_class:
                huey_backend = "sqlite"
        # Get queue depth
        queue_depth = huey.pending_count()
    except Exception as e:
        worker_status = "error"
        huey_backend = "error"
        queue_depth = 0

    return {
        "status": "ok",
        "database": db_status,
        "worker": worker_status,
        "huey_backend": huey_backend,
        "queue_depth": queue_depth
    }