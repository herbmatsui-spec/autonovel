import asyncio
import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Response, status
from pydantic import BaseModel

from config import get_config
from src.backend.config import settings
from src.backend.health.checks import (
    HealthCheckResult,
    HealthStatus,
    check_chromadb,
    check_database,
    check_llm_gateway,
    check_redis,
    check_worker,
    check_enrichment_agent,
)
from src.core.container import AppContainer

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


class CheckResponse(BaseModel):
    status: HealthStatus
    latency_ms: float | None = None
    details: str = ""
    error: str = ""


class HealthResponse(BaseModel):
    status: HealthStatus
    version: str = settings.APP_VERSION
    timestamp: str
    checks: dict[str, CheckResponse]


class LivenessResponse(BaseModel):
    status: str = "alive"
    timestamp: str


@router.get("/health/live")
@router.get("/health/liveness")
async def health_liveness():
    """Liveness Probe: プロセスが生きているか即座に応答（外部依存なし）"""
    return {"status": "alive"}


@router.get("/health/ready")
async def health_ready():
    """
    Readiness probe: checks if dependencies (e.g., database) are available.
    Returns 200 when all dependencies are healthy, 503 with error payload otherwise.
    """
    from fastapi.responses import JSONResponse
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


class ReadinessResponse(BaseModel):
    status: str  # "ready" or "not_ready"
    dependencies: dict[str, str]
    timestamp: str


@router.get("/health/readiness", response_model=ReadinessResponse)
async def health_readiness(response: Response):
    """Readiness Probe: DBなどの主要外部依存が準備完了しているか検証"""
    cfg = get_config()
    db_manager = AppContainer.db()

    # 主要なDBとRedisの疎通を確認
    db_res = await check_database(db_manager)
    redis_res = await check_redis(cfg.redis_url)

    deps = {
        "database": db_res.status.value,
        "redis": redis_res.status.value,
    }

    # DBがエラーの場合はトラフィックを送らせないため 503 Service Unavailable を設定
    if db_res.status == HealthStatus.ERROR:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="not_ready",
            dependencies=deps,
            timestamp=datetime.now(UTC).isoformat(),
        )

    return ReadinessResponse(
        status="ready",
        dependencies=deps,
        timestamp=datetime.now(UTC).isoformat(),
    )


def determine_overall_status(checks: dict[str, HealthCheckResult]) -> HealthStatus:
    """個別チェック結果から総合ステータスを決定"""
    statuses = [c.status for c in checks.values()]
    if HealthStatus.ERROR in statuses:
        return HealthStatus.ERROR
    if HealthStatus.DEGRADED in statuses:
        return HealthStatus.DEGRADED
    # NOT_CONFIGURED は警告だが全体を unhealthy にはしない
    return HealthStatus.OK


@router.get("/health/detail", response_model=HealthResponse)
async def health_check():
    """拡張ヘルスチェック: DB, Redis, ChromaDB, LLM Gateway, Worker を並列チェック"""
    cfg = get_config()
    db_manager = AppContainer.db()

    # 並列実行でレイテンシ短縮
    results = await asyncio.gather(
        check_database(db_manager),
        check_redis(cfg.redis_url),
        check_chromadb(),
        check_llm_gateway(settings.GEMINI_API_KEY),
        check_worker(),
        check_enrichment_agent(),
        return_exceptions=True,
    )

    check_names = ["database", "redis", "chromadb", "llm_gateway", "worker", "enrichment_agent"]
    checks: dict[str, HealthCheckResult] = {}
    check_responses: dict[str, CheckResponse] = {}

    for name, result in zip(check_names, results):
        if isinstance(result, Exception):
            checks[name] = HealthCheckResult(status=HealthStatus.ERROR, error=str(result))
            check_responses[name] = CheckResponse(status=HealthStatus.ERROR, error=str(result))
        elif isinstance(result, HealthCheckResult):
            checks[name] = result
            check_responses[name] = CheckResponse(
                status=result.status,
                latency_ms=result.latency_ms,
                details=result.details,
                error=result.error,
            )
        else:
            checks[name] = HealthCheckResult(
                status=HealthStatus.ERROR, error="Unexpected result type"
            )
            check_responses[name] = CheckResponse(
                status=HealthStatus.ERROR, error="Unexpected result type"
            )

    overall = determine_overall_status(checks)

    return HealthResponse(
        status=overall, timestamp=datetime.now(UTC).isoformat(), checks=check_responses
    )
