from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

@router.get("/health/live")
async def liveness():
    """
    Liveness probe: returns 200 if the application is running.
    """
    return {"status": "alive"}

@router.get("/health/ready")
async def readiness():
    """
    Readiness probe: checks if dependencies (e.g., database) are available.
    In a real application, you would check the database connection, cache, etc.
    For now, we return a placeholder.
    """
    # TODO: Add actual dependency checks (e.g., database connection)
    try:
        # Example: check database connection
        # from src.backend.database import get_db
        # db = get_db()
        # db.execute("SELECT 1")
        pass
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not ready", "error": str(e)}, 503
    return {"status": "ready"}