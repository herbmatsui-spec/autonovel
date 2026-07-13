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
    try:
        from src.backend.tasks import huey
        huey.pending_count()
    except Exception:
        worker_status = "error"

    return {
        "status": "ok",
        "database": db_status,
        "worker": worker_status
    }
