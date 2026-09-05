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

book_score_trend = Gauge(
    "book_score_trend",
    "BookScore trend (3-chapter moving average and slope)",
    ["book_id", "metric"],  # metric: avg_overall, slope
)

skill_version_active = Gauge(
    "skill_version_active",
    "Active skill version (1=v1, 2=v2)",
    ["skill_name"],
)

book_score_promotion_eligible = Counter(
    "book_score_promotion_eligible_total",
    "Number of books eligible for promotion",
    ["book_id"],
)

book_score_improvement_priority = Gauge(
    "book_score_improvement_priority",
    "BookScore improvement priority score (lower = higher priority)",
    ["book_id", "dimension"],
)

ab_test_result_total = Counter(
    "ab_test_result_total",
    "Total number of A/B tests executed",
    ["skill_name", "winner"],  # winner: a, b, tie
)

ab_test_duration_seconds = Histogram(
    "ab_test_duration_seconds",
    "A/B test execution duration",
    ["skill_name", "version"],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

ab_test_success_rate = Gauge(
    "ab_test_success_rate",
    "A/B test success rate per version",
    ["skill_name", "version"],
)

book_score_alert_total = Counter(
    "book_score_alert_total",
    "Total number of BookScore alerts triggered",
    ["book_id", "alert_type"],  # alert_type: score_drop, stagnation, anomaly, no_improvement
)

book_score_forecast = Gauge(
    "book_score_forecast",
    "BookScore forecast for next chapter",
    ["book_id"],
)

skill_promotion_total = Counter(
    "skill_promotion_total",
    "Total number of skill promotions from A/B test",
    ["skill_name", "promoted_version"],  # promoted_version: v1, v2
)


# ===================== Phase 3 共通メトリクス =====================
def record_phase3_operation(component: str, operation: str, duration: float, status: str):
    """Phase 3 共通操作メトリクスを記録"""
    phase3_operation_duration_seconds.labels(component=component, operation=operation, status=status).observe(duration)
    phase3_operation_total.labels(component=component, operation=operation, status=status).inc()


# Phase 3 共通操作メトリクス
phase3_operation_duration_seconds = Histogram(
    "phase3_operation_duration_seconds",
    "Phase 3 component operation duration in seconds",
    ["component", "operation", "status"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
)

phase3_operation_total = Counter(
    "phase3_operation_total",
    "Total Phase 3 component operations",
    ["component", "operation", "status"],
)


def record_ab_test_result(skill_name: str, winner: str, version_a: str, version_b: str, 
                          duration: float, success_rate_a: float, success_rate_b: float):
    """A/Bテスト結果を記録"""
    ab_test_result_total.labels(skill_name=skill_name, winner=winner).inc()
    ab_test_duration_seconds.labels(skill_name=skill_name, version="a").observe(duration)
    ab_test_duration_seconds.labels(skill_name=skill_name, version="b").observe(duration)
    ab_test_success_rate.labels(skill_name=skill_name, version="a").set(success_rate_a)
    ab_test_success_rate.labels(skill_name=skill_name, version="b").set(success_rate_b)


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
    
    # トレンドメトリクス（書籍IDが含まれている場合）
    book_id = score.get("book_id")
    if book_id and "trend_3ch" in score and score["trend_3ch"]:
        trend = score["trend_3ch"]
        book_score_trend.labels(book_id=str(book_id), metric="avg_overall").set(
            trend.get("avg_overall_score", 0)
        )
        book_score_trend.labels(book_id=str(book_id), metric="slope").set(
            trend.get("trend_slope", 0)
        )

    # 昇格判定メトリクス（昇格条件チェック時に呼び出す想定）
    # ここでは記録しない（API呼び出し時に記録）

    # 改善優先順位メトリクス
    if book_id:
        for dim in ["structure", "coherency", "factual_grounding", "visual_textual_synergy", "reader_experience"]:
            val = score.get(f"{dim}_score", 0)
            # 低スコアほど高い優先度（優先度 = 100 - score）
            priority = 100 - val
            book_score_improvement_priority.labels(book_id=str(book_id), dimension=dim).set(priority)


def record_promotion_eligible(book_id: int, eligible: bool):
    """昇格判定結果を記録"""
    if eligible:
        book_score_promotion_eligible.labels(book_id=str(book_id)).inc()


def record_skill_version(skill_name: str, version: str):
    """アクティブなスキルバージョンを記録"""
    version_num = 1 if version == "v1" else (2 if version == "v2" else 0)
    skill_version_active.labels(skill_name=skill_name).set(version_num)


def record_skill_promotion(skill_name: str, promoted_version: str):
    """スキル昇格を記録"""
    skill_promotion_total.labels(skill_name=skill_name, promoted_version=promoted_version).inc()
    # バージョンも更新
    record_skill_version(skill_name, promoted_version)


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


def record_book_score_alert(book_id: int, alert_type: str):
    """BookScore アラート発生を記録"""
    book_score_alert_total.labels(book_id=str(book_id), alert_type=alert_type).inc()


def record_book_score_forecast(book_id: int, forecast_score: float):
    """BookScore 予測値を記録"""
    book_score_forecast.labels(book_id=str(book_id)).set(forecast_score)


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


# ===================== Phase 4: Enrichment Agent =====================
enrichment_duration_seconds = Histogram(
    "enrichment_duration_seconds",
    "EnrichmentAgent execution duration in seconds",
    ["status"],  # success, error, skipped
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
)

enrichment_trivia_insertions_total = Counter(
    "enrichment_trivia_insertions_total",
    "Total trivia insertions by EnrichmentAgent",
    ["book_id", "status"],  # status: inserted, skipped
)

enrichment_citations_added_total = Counter(
    "enrichment_citations_added_total",
    "Total citations added by EnrichmentAgent",
    ["book_id", "style"],  # style: footnote, bracket, endnote
)

enrichment_sensory_expansions_total = Counter(
    "enrichment_sensory_expansions_total",
    "Total sensory expansions by EnrichmentAgent",
    ["book_id", "emotion"],
)

enrichment_multimedia_scenarios_total = Counter(
    "enrichment_multimedia_scenarios_total",
    "Total multimedia scenarios generated by EnrichmentAgent",
    ["book_id", "format"],  # format: manga_script, radio_drama, anime_storyboard, live_action_shots
)

enrichment_token_usage = Histogram(
    "enrichment_token_usage",
    "Token usage delta by EnrichmentAgent (enriched - original)",
    ["book_id"],
    buckets=[0, 100, 250, 500, 1000, 2000, 5000, 10000],
)

enrichment_errors_total = Counter(
    "enrichment_errors_total",
    "Total EnrichmentAgent errors",
    ["error_type", "stage"],  # stage: trivia, citation, sensory, multimedia, budget
)


def record_enrichment_metrics(
    book_id: int,
    duration: float,
    status: str,
    trivia_count: int = 0,
    citation_count: int = 0,
    sensory_count: int = 0,
    multimedia_formats: list[str] | None = None,
    token_delta: int = 0,
    error: str | None = None,
):
    """EnrichmentAgent 実行メトリクスを記録"""
    enrichment_duration_seconds.labels(status=status).observe(duration)
    
    if trivia_count > 0:
        enrichment_trivia_insertions_total.labels(book_id=str(book_id), status="inserted").inc(trivia_count)
    
    if citation_count > 0:
        # style は設定から取得（デフォルト footnote）
        enrichment_citations_added_total.labels(book_id=str(book_id), style="footnote").inc(citation_count)
    
    if sensory_count > 0:
        enrichment_sensory_expansions_total.labels(book_id=str(book_id), emotion="mixed").inc(sensory_count)
    
    if multimedia_formats:
        for fmt in multimedia_formats:
            enrichment_multimedia_scenarios_total.labels(book_id=str(book_id), format=fmt).inc()
    
    if token_delta > 0:
        enrichment_token_usage.labels(book_id=str(book_id)).observe(token_delta)
    
    if error:
        stage = "unknown"
        if "trivia" in error.lower():
            stage = "trivia"
        elif "citation" in error.lower():
            stage = "citation"
        elif "sensory" in error.lower():
            stage = "sensory"
        elif "multimedia" in error.lower():
            stage = "multimedia"
        elif "budget" in error.lower() or "token" in error.lower():
            stage = "budget"
        enrichment_errors_total.labels(error_type=type(error).__name__, stage=stage).inc()


# ===================== Phase 2: Blind Review / Specialist Audit / Reflective RAG =====================
# Blind Peer Review
blind_review_blocked_keys_total = Counter(
    "blind_review_blocked_keys_total",
    "Total keys blocked by BlindReviewGate",
    ["gate", "source_agent"],
)

# Specialist Audit
specialist_audit_duration_seconds = Histogram(
    "specialist_audit_duration_seconds",
    "Specialist auditor execution duration",
    ["specialist", "status"],
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

specialist_audit_score = Gauge(
    "specialist_audit_score",
    "Specialist auditor score (0-100)",
    ["specialist", "book_id", "chapter"],
)

# Reflective RAG
reflective_rag_iterations = Histogram(
    "reflective_rag_iterations",
    "Reflective RAG iterations per retrieval",
    ["book_id"],
    buckets=[1, 2, 3, 4, 5],
)

reflective_rag_convergence_total = Counter(
    "reflective_rag_convergence_total",
    "Reflective RAG convergence outcomes",
    ["converged"],
)

reflective_rag_threshold_filtered_total = Counter(
    "reflective_rag_threshold_filtered_total",
    "Documents filtered by relevance threshold in Reflective RAG",
    ["book_id"],
)

reflective_rag_query_refinements_total = Counter(
    "reflective_rag_query_refinements_total",
    "Total query refinements performed in Reflective RAG",
    ["book_id"],
)


def reset():
    """テスト用リセット関数"""
    from src.backend.observability.health import metrics as h_metrics

    h_metrics.reset()
