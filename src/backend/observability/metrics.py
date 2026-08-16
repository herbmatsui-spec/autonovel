"""
src/backend/observability/metrics.py - Prometheus メトリクス定義・公開

命名規約: kaku_{subsystem}_{name}_{unit}
- subsystem: http, novel, llm, db, huey, chromadb, redis
- name: 説明的な名前
- unit: total, seconds, bytes, active, idle, depth, connected
"""

import time
from functools import wraps
from typing import Any, Callable

from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

# ===================== 標準 HTTP メトリクス =====================
kaku_http_requests_total = Counter(
    "kaku_http_requests_total", "Total HTTP requests", ["method", "path", "status"]
)

kaku_http_request_duration_seconds = Histogram(
    "kaku_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

kaku_http_requests_in_progress = Gauge(
    "kaku_http_requests_in_progress", "HTTP requests currently in progress", ["method", "path"]
)

# ===================== アプリ固有メトリクス =====================
kaku_novel_generation_tasks_total = Counter(
    "kaku_novel_generation_tasks_total",
    "Total novel generation tasks",
    ["workflow_type", "status"],  # status: started, completed, failed
)

kaku_novel_generation_duration_seconds = Histogram(
    "kaku_novel_generation_duration_seconds",
    "Novel generation duration in seconds",
    ["workflow_type"],
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600],
)

kaku_llm_api_calls_total = Counter(
    "kaku_llm_api_calls_total",
    "Total LLM API calls",
    ["model", "status"],  # status: success, error, timeout
)

kaku_llm_tokens_total = Counter(
    "kaku_llm_tokens_total",
    "Total LLM tokens used",
    ["model", "token_type"],  # token_type: prompt, completion
)

kaku_db_pool_connections_active = Gauge(
    "kaku_db_pool_connections_active", "Active database connections in pool"
)

kaku_db_pool_connections_idle = Gauge(
    "kaku_db_pool_connections_idle", "Idle database connections in pool"
)

kaku_huey_queue_depth = Gauge("kaku_huey_queue_depth", "Huey task queue depth")

kaku_huey_tasks_processed_total = Counter(
    "kaku_huey_tasks_processed_total",
    "Total Huey tasks processed",
    ["status"],  # success, error, retry
)

kaku_chromadb_collections = Gauge("kaku_chromadb_collections", "Number of ChromaDB collections")

kaku_redis_clients_connected = Gauge("kaku_redis_clients_connected", "Number of connected Redis clients")


# ===================== 後方互換エイリアス (段階的移行用) =====================
# 旧メトリクス名への参照を維持（将来的に削除予定）
http_requests_total = kaku_http_requests_total
http_request_duration_seconds = kaku_http_request_duration_seconds
http_requests_in_progress = kaku_http_requests_in_progress
novel_generation_tasks_total = kaku_novel_generation_tasks_total
novel_generation_duration_seconds = kaku_novel_generation_duration_seconds
llm_api_calls_total = kaku_llm_api_calls_total
llm_api_tokens_total = kaku_llm_tokens_total
db_pool_connections_active = kaku_db_pool_connections_active
db_pool_connections_idle = kaku_db_pool_connections_idle
huey_queue_depth = kaku_huey_queue_depth
huey_tasks_processed_total = kaku_huey_tasks_processed_total
chromadb_collections = kaku_chromadb_collections
redis_connected_clients = kaku_redis_clients_connected


# ===================== ユーティリティ関数 =====================
def record_http_metrics(method: str, path: str, status: int, duration: float):
    kaku_http_requests_total.labels(method=method, path=path, status=str(status)).inc()
    kaku_http_request_duration_seconds.labels(method=method, path=path).observe(duration)


def record_generation_task(workflow_type: str, status: str, duration: float = None):
    kaku_novel_generation_tasks_total.labels(workflow_type=workflow_type, status=status).inc()
    if duration is not None:
        kaku_novel_generation_duration_seconds.labels(workflow_type=workflow_type).observe(duration)


def record_llm_call(model: str, status: str, prompt_tokens: int = 0, completion_tokens: int = 0):
    kaku_llm_api_calls_total.labels(model=model, status=status).inc()
    if prompt_tokens:
        kaku_llm_tokens_total.labels(model=model, token_type="prompt").inc(prompt_tokens)
    if completion_tokens:
        kaku_llm_tokens_total.labels(model=model, token_type="completion").inc(completion_tokens)


def update_db_pool_metrics(active: int, idle: int):
    kaku_db_pool_connections_active.set(active)
    kaku_db_pool_connections_idle.set(idle)


def update_huey_queue_depth(depth: int):
    kaku_huey_queue_depth.set(depth)


def record_huey_task(status: str):
    kaku_huey_tasks_processed_total.labels(status=status).inc()


def update_chromadb_collections(count: int):
    kaku_chromadb_collections.set(count)


def update_redis_clients(count: int):
    kaku_redis_clients_connected.set(count)


# ===================== /metrics エンドポイント用 =====================
async def metrics_endpoint() -> Response:
    """Prometheus メトリクス公開エンドポイント"""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ===================== デコレータ（任意） =====================
def track_llm_metrics(model: str):
    """LLM 呼び出し関数をラップしてメトリクス記録"""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                duration = time.perf_counter() - start
                record_llm_call(model, "success")
                return result
            except Exception:
                record_llm_call(model, "error")
                raise

        return wrapper

    return decorator


# ===================== ミドルウェア用ヘルパー =====================
class MetricsMiddleware:
    """HTTP メトリクス収集ミドルウェア"""

    def __init__(self):
        self._path_normalizer = PathNormalizer()

    async def __call__(self, request, call_next):
        method = request.method
        path = self._path_normalizer.normalize(request.url.path)

        kaku_http_requests_in_progress.labels(method=method, path=path).inc()
        start = time.perf_counter()
        try:
            response = await call_next(request)
            duration = time.perf_counter() - start
            record_http_metrics(method, path, response.status_code, duration)
            return response
        except Exception:
            duration = time.perf_counter() - start
            record_http_metrics(method, path, 500, duration)
            raise
        finally:
            kaku_http_requests_in_progress.labels(method=method, path=path).dec()


class PathNormalizer:
    """パスパラメータを正規化してカーディナリティを制御"""

    def __init__(self):
        import re

        self._patterns = [
            (re.compile(r"/api/books/\d+"), "/api/books/{id}"),
            (re.compile(r"/api/episodes/\d+"), "/api/episodes/{id}"),
            (re.compile(r"/api/tasks/[a-zA-Z0-9_-]+"), "/api/tasks/{id}"),
            (re.compile(r"/api/plots/\d+"), "/api/plots/{id}"),
            (re.compile(r"/api/chapters/\d+"), "/api/chapters/{id}"),
            (re.compile(r"/api/prompt-versions/\d+"), "/api/prompt-versions/{id}"),
        ]

    def normalize(self, path: str) -> str:
        for pattern, replacement in self._patterns:
            path = pattern.sub(replacement, path)
        return path
