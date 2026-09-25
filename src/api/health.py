from fastapi import APIRouter
from fastapi.responses import JSONResponse
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
    Returns 200 when all dependencies are healthy, 503 with error payload otherwise.
    """
    checks = {}
    try:
        from src.backend.observability.health import check_database
        db_res = await check_database(timeout=2.0)
        checks["database"] = db_res
        if db_res.get("status") != "ok":
            return JSONResponse(
                status_code=503,
                content={"status": "not ready", "error": db_res.get("code", "DB_ERROR"), "checks": checks},
            )
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={"status": "not ready", "error": str(e), "checks": checks},
        )
    return {"status": "ready", "checks": checks}