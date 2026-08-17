import logging
from datetime import datetime, timezone
from typing import Dict, Optional
import asyncio

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.core.container import AppContainer
from config.settings import get_settings
from src.backend.health.checks import (
    check_database,
    check_redis,
    check_chromadb,
    check_llm_gateway,
    check_worker,
    HealthStatus,
    HealthCheckResult,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


class CheckResponse(BaseModel):
    status: HealthStatus
    latency_ms: Optional[float] = None
    details: str = ""
    error: str = ""


class HealthResponse(BaseModel):
    status: HealthStatus
    version: str = "3.0.0"
    timestamp: str
    checks: Dict[str, CheckResponse]


def determine_overall_status(checks: Dict[str, HealthCheckResult]) -> HealthStatus:
    """個別チェック結果から総合ステータスを決定"""
    statuses = [c.status for c in checks.values()]
    if HealthStatus.ERROR in statuses:
        return HealthStatus.ERROR
    if HealthStatus.DEGRADED in statuses:
        return HealthStatus.DEGRADED
    # NOT_CONFIGURED は警告だが全体を unhealthy にはしない
    return HealthStatus.OK


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """拡張ヘルスチェック: DB, Redis, ChromaDB, LLM Gateway, Worker を並列チェック"""
    cfg = get_settings()
    db_manager = AppContainer.db()

    # 並列実行でレイテンシ短縮
    results = await asyncio.gather(
        check_database(db_manager),
        check_redis(cfg.redis_url),
        check_chromadb(),
        check_llm_gateway(cfg.openai_api_key),
        check_worker(),
        return_exceptions=True
    )

    check_names = ["database", "redis", "chromadb", "llm_gateway", "worker"]
    checks: Dict[str, HealthCheckResult] = {}
    check_responses: Dict[str, CheckResponse] = {}

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
                error=result.error
            )
        else:
            checks[name] = HealthCheckResult(status=HealthStatus.ERROR, error="Unexpected result type")
            check_responses[name] = CheckResponse(status=HealthStatus.ERROR, error="Unexpected result type")

    overall = determine_overall_status(checks)

    return HealthResponse(
        status=overall,
        timestamp=datetime.now(timezone.utc).isoformat(),
        checks=check_responses
    )