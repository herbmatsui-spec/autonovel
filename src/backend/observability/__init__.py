# src/backend/observability/__init__.py
from .metrics import (
    # ミドルウェア
    MetricsMiddleware,
    chromadb_collections,
    db_pool_connections_active,
    db_pool_connections_idle,
    http_request_duration_seconds,
    http_requests_in_progress,
    # 標準 HTTP メトリクス
    http_requests_total,
    huey_queue_depth,
    huey_tasks_processed_total,
    llm_api_calls_total,
    llm_api_tokens_total,
    # エンドポイント
    metrics_endpoint,
    novel_generation_duration_seconds,
    # アプリ固有メトリクス
    novel_generation_tasks_total,
    record_generation_task,
    # ユーティリティ
    record_http_metrics,
    record_huey_task,
    record_llm_call,
    redis_connected_clients,
    # デコレータ
    track_llm_metrics,
    update_chromadb_collections,
    update_db_pool_metrics,
    update_huey_queue_depth,
    update_redis_clients,
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
