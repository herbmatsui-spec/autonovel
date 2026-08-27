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
@router.get("/api/health", response_model=HealthResponse)
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


# ステップ 68: Continuity Check エンドポイント
class ContinuityCheckRequest(BaseModel):
    enabled: bool = True
    scene: Dict[str, Any]
    prev_scene: Optional[Dict[str, Any]] = None


class ContinuityCheckResponse(BaseModel):
    valid: bool
    violations: List[Dict[str, Any]] = Field(default_factory=list)
    report: str = ""


@router.post("/api/continuity/check", response_model=ContinuityCheckResponse)
async def check_continuity_endpoint(req: ContinuityCheckRequest):
    """シーン連続性チェック用 API (ステップ 68)"""
    if not req.enabled:
        return ContinuityCheckResponse(valid=True, violations=[], report="")

    try:
        import os
        from novel_50ep.scene_model import SceneBase
        from novel_50ep.continuity_tracker import ContinuityTracker

        rules_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../novel_50ep/continuity_rules")
        )
        tracker = ContinuityTracker(rules_dir=rules_dir)
        if req.prev_scene:
            prev_s = SceneBase.from_dict(req.prev_scene)
            tracker.feed(prev_s)
        cur_s = SceneBase.from_dict(req.scene)
        violations = tracker.feed(cur_s)
        return ContinuityCheckResponse(
            valid=len(violations) == 0,
            violations=violations,
            report=tracker.report(),
        )
    except Exception as e:
        logger.warning(f"Continuity check error: {e}")
        return ContinuityCheckResponse(
            valid=False,
            violations=[{"field": "system", "msg": str(e)}],
            report=str(e),
        )