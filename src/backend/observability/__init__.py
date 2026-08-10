# src/backend/observability/__init__.py
from .metrics import (
    # 標準 HTTP メトリクス
    http_requests_total,
    http_request_duration_seconds,
    http_requests_in_progress,
    # アプリ固有メトリクス
    novel_generation_tasks_total,
    novel_generation_duration_seconds,
    llm_api_calls_total,
    llm_api_tokens_total,
    db_pool_connections_active,
    db_pool_connections_idle,
    huey_queue_depth,
    huey_tasks_processed_total,
    chromadb_collections,
    redis_connected_clients,
    # ユーティリティ
    record_http_metrics,
    record_generation_task,
    record_llm_call,
    update_db_pool_metrics,
    update_huey_queue_depth,
    record_huey_task,
    update_chromadb_collections,
    update_redis_clients,
    # エンドポイント
    metrics_endpoint,
    # ミドルウェア
    MetricsMiddleware,
    # デコレータ
    track_llm_metrics,
)

__all__ = [
    "http_requests_total",
    "http_request_duration_seconds",
    "http_requests_in_progress",
    "novel_generation_tasks_total",
    "novel_generation_duration_seconds",
    "llm_api_calls_total",
    "llm_api_tokens_total",
    "db_pool_connections_active",
    "db_pool_connections_idle",
    "huey_queue_depth",
    "huey_tasks_processed_total",
    "chromadb_collections",
    "redis_connected_clients",
    "record_http_metrics",
    "record_generation_task",
    "record_llm_call",
    "update_db_pool_metrics",
    "update_huey_queue_depth",
    "record_huey_task",
    "update_chromadb_collections",
    "update_redis_clients",
    "metrics_endpoint",
    "MetricsMiddleware",
    "track_llm_metrics",
]