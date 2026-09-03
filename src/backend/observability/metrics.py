"""
src/backend/observability/metrics.py - Prometheus メトリクス定義・公開
"""

import time
from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

# ===================== 標準 HTTP メトリクス =====================
http_requests_total = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status"]
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

http_requests_in_progress = Gauge(
    "http_requests_in_progress", "HTTP requests currently in progress", ["method", "path"]
)

# ===================== アプリ固有メトリクス =====================
novel_generation_tasks_total = Counter(
    "novel_generation_tasks_total",
    "Total novel generation tasks",
    ["workflow_type", "status"],  # status: started, completed, failed
)

novel_generation_duration_seconds = Histogram(
    "novel_generation_duration_seconds",
    "Novel generation duration in seconds",
    ["workflow_type"],
    buckets=[10, 30, 60, 120, 300, 600, 1800, 3600],
)

llm_api_calls_total = Counter(
    "llm_api_calls_total",
    "Total LLM API calls",
    ["model", "status"],  # status: success, error, timeout
)

llm_api_tokens_total = Counter(
    "llm_api_tokens_total",
    "Total LLM tokens used",
    ["model", "token_type"],  # token_type: prompt, completion
)

db_pool_connections_active = Gauge(
    "db_pool_connections_active", "Active database connections in pool"
)

db_pool_connections_idle = Gauge("db_pool_connections_idle", "Idle database connections in pool")

huey_queue_depth = Gauge("huey_queue_depth", "Huey task queue depth")

huey_tasks_processed_total = Counter(
    "huey_tasks_processed_total",
    "Total Huey tasks processed",
    ["status"],  # success, error, retry
)

chromadb_collections = Gauge("chromadb_collections", "Number of ChromaDB collections")

redis_connected_clients = Gauge("redis_connected_clients", "Number of connected Redis clients")

# ===================== BookScore メトリクス =====================
book_score_overall = Histogram(
    "book_score_overall",
    "BookScore overall score distribution",
    ["genre", "phase"],
    buckets=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
)

book_score_dimensions = Histogram(
    "book_score_dimensions",
    "BookScore dimension scores",
    ["dimension"],  # structure, coherency, factual, visual_textual, reader_exp
    buckets=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
)

book_score_regeneration_triggered = Counter(
    "book_score_regeneration_triggered_total",
    "Number of times BookScore triggered regeneration",
    ["dimension"],
)


def record_book_score(score: dict, genre: str = "", phase: str = ""):
    """BookScore メトリクスを記録"""
    book_score_overall.labels(genre=genre or "unknown", phase=phase or "writing").observe(
        score.get("overall_score", 0)
    )
    for dim in ["structure", "coherency", "factual_grounding", "visual_textual_synergy", "reader_experience"]:
        val = score.get(f"{dim}_score", 0)
        book_score_dimensions.labels(dimension=dim).observe(val)
    if score.get("regeneration_triggered"):
        for dim in score.get("low_dimensions", []):
            book_score_regeneration_triggered.labels(dimension=dim).inc()


# ===================== ユーティリティ関数 =====================
def record_http_metrics(method: str, path: str, status: int, duration: float):
    http_requests_total.labels(method=method, path=path, status=str(status)).inc()
    http_request_duration_seconds.labels(method=method, path=path).observe(duration)


def record_generation_task(workflow_type: str, status: str, duration: float | None = None):
    novel_generation_tasks_total.labels(workflow_type=workflow_type, status=status).inc()
    if duration is not None:
        novel_generation_duration_seconds.labels(workflow_type=workflow_type).observe(duration)


def record_llm_call(model: str, status: str, prompt_tokens: int = 0, completion_tokens: int = 0):
    llm_api_calls_total.labels(model=model, status=status).inc()
    if prompt_tokens:
        llm_api_tokens_total.labels(model=model, type="prompt").inc(prompt_tokens)
    if completion_tokens:
        llm_api_tokens_total.labels(model=model, type="completion").inc(completion_tokens)


def update_db_pool_metrics(active: int, idle: int):
    db_pool_connections_active.set(active)
    db_pool_connections_idle.set(idle)


def update_huey_queue_depth(depth: int):
    huey_queue_depth.set(depth)


def record_huey_task(status: str):
    huey_tasks_processed_total.labels(status=status).inc()


def update_chromadb_collections(count: int):
    chromadb_collections.set(count)


def update_redis_clients(count: int):
    redis_connected_clients.set(count)


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
            try:
                result = await func(*args, **kwargs)
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

        http_requests_in_progress.labels(method=method, path=path).inc()
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
            http_requests_in_progress.labels(method=method, path=path).dec()


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


def reset():
    """テスト用リセット関数"""
    from src.backend.observability.health import metrics as h_metrics

    h_metrics.reset()
