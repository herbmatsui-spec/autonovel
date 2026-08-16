"""
src/backend/health/checks.py - ヘルスチェック共通ロジック
各依存サービスの疎通確認を実装し、統一された結果形式で返す。
"""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    ERROR = "error"
    NOT_CONFIGURED = "not_configured"


@dataclass
class HealthCheckResult:
    status: HealthStatus
    latency_ms: Optional[float] = None
    details: str = ""
    error: str = ""


async def check_database(db_manager) -> HealthCheckResult:
    """DB 接続プールから接続取得 + SELECT 1"""
    start = time.perf_counter()
    try:
        from sqlalchemy import text

        async with db_manager.engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        latency = (time.perf_counter() - start) * 1000
        pool = db_manager.engine.pool
        checked_in = pool.checkedin() if hasattr(pool, "checkedin") else 0
        pool_size = pool.size() if hasattr(pool, "size") else 0
        return HealthCheckResult(
            status=HealthStatus.OK, latency_ms=latency, details=f"pool={checked_in}/{pool_size}"
        )
    except Exception as e:
        logger.warning(f"DB health check failed: {e}")
        return HealthCheckResult(status=HealthStatus.ERROR, error=str(e))


async def check_redis(redis_url: Optional[str]) -> HealthCheckResult:
    """Redis PING + INFO clients"""
    if not redis_url:
        return HealthCheckResult(
            status=HealthStatus.NOT_CONFIGURED, error="REDIS_URL not configured"
        )
    start = time.perf_counter()
    try:
        import redis.asyncio as redis

        client = redis.from_url(redis_url, socket_connect_timeout=2, socket_timeout=2)
        await client.ping()
        info = await client.info("clients")
        await client.close()
        latency = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            status=HealthStatus.OK,
            latency_ms=latency,
            details=f"connected_clients={info.get('connected_clients', '?')}",
        )
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return HealthCheckResult(status=HealthStatus.ERROR, error=str(e))


async def check_chromadb() -> HealthCheckResult:
    """ChromaDB ハートビート + コレクション一覧"""
    start = time.perf_counter()
    try:
        from src.core.container import AppContainer

        client = AppContainer.chroma_client_provider()
        if not client:
            return HealthCheckResult(
                status=HealthStatus.NOT_CONFIGURED, error="ChromaDB not initialized"
            )
        client.heartbeat()
        collections = client.list_collections()
        latency = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            status=HealthStatus.OK, latency_ms=latency, details=f"collections={len(collections)}"
        )
    except Exception as e:
        logger.warning(f"ChromaDB health check failed: {e}")
        return HealthCheckResult(status=HealthStatus.ERROR, error=str(e))


async def check_llm_gateway(api_key: Optional[str]) -> HealthCheckResult:
    """LLM Gateway 軽量呼び出し（モデル一覧 or 短い生成）"""
    import os

    # ヘルスチェックでの LLM 呼び出しを無効化する環境変数
    if os.getenv("KAKU_HEALTH_CHECK_LLM", "true").lower() == "false":
        return HealthCheckResult(
            status=HealthStatus.NOT_CONFIGURED, details="LLM check disabled via env"
        )

    if not api_key or api_key == "DUMMY":
        return HealthCheckResult(status=HealthStatus.NOT_CONFIGURED, error="API key not configured")
    start = time.perf_counter()
    try:
        from src.core.llm_gateway import LLMProviderFactory, create_genai_client

        genai_client = create_genai_client(api_key=api_key)
        factory = LLMProviderFactory(genai_client=genai_client)
        # ごく短いテスト生成（1 token 程度）
        result = await factory.generate_text(
            model="gemini-3.5-flash-lite", prompt="ping", max_tokens=1, temperature=0.0
        )
        latency = (time.perf_counter() - start) * 1000
        return HealthCheckResult(
            status=HealthStatus.OK if result else HealthStatus.ERROR,
            latency_ms=latency,
            details=f"model=gemini-3.5-flash-lite, response_len={len(result) if result else 0}",
        )
    except Exception as e:
        logger.warning(f"LLM Gateway health check failed: {e}")
        return HealthCheckResult(status=HealthStatus.ERROR, error=str(e))


async def check_worker() -> HealthCheckResult:
    """Huey ワーカー状態"""
    try:
        from src.backend.tasks import huey

        backend_class = huey.backend.__class__.__name__ if hasattr(huey, "backend") else "unknown"
        huey_backend = (
            "redis"
            if "Redis" in backend_class
            else "sqlite"
            if "Sqlite" in backend_class
            else "unknown"
        )
        queue_depth = huey.pending_count()
        return HealthCheckResult(
            status=HealthStatus.OK,
            details=f"huey_backend={huey_backend}, queue_depth={queue_depth}",
        )
    except Exception as e:
        logger.warning(f"Worker health check failed: {e}")
        return HealthCheckResult(status=HealthStatus.ERROR, error=str(e))
