"""
OpenTelemetry 自動計装設定
FastAPI, SQLAlchemy, Redis, ChromaDB 等の自動計装を提供
"""

from __future__ import annotations

import os
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

from config.settings import get_settings


def setup_opentelemetry(
    service_name: Optional[str] = None,
    otlp_endpoint: Optional[str] = None,
    enable_console_exporter: bool = False,
    sample_rate: float = 0.1,
) -> TracerProvider:
    """
    OpenTelemetry を初期化し、自動計装を有効化する。

    Args:
        service_name: サービス名（未指定時は設定から取得）
        otlp_endpoint: OTLP エンドポイント（未指定時は環境変数 OTEL_EXPORTER_OTLP_ENDPOINT）
        enable_console_exporter: コンソールエクスポーターを有効化（デバッグ用）
        sample_rate: トレースサンプリングレート (0.0-1.0)

    Returns:
        TracerProvider インスタンス
    """
    settings = get_settings()

    # サービス名決定
    if service_name is None:
        service_name = os.getenv("OTEL_SERVICE_NAME", "kaku-hegemony-engine")

    # OTLP エンドポイント決定
    if otlp_endpoint is None:
        otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")

    # リソース作成
    resource = Resource.create({
        SERVICE_NAME: service_name,
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })

    # TracerProvider 作成
    provider = TracerProvider(
        resource=resource,
        sampler=TraceIdRatioBased(sample_rate),
    )

    # エクスポーター設定
    if enable_console_exporter:
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))

    # OTLP エクスポーター（本番環境用）
    if otlp_endpoint and not enable_console_exporter:
        try:
            otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
            provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        except Exception as e:
            # OTLP エクスポーターの初期化に失敗しても続行（コンソールのみ等）
            import logging
            logging.getLogger(__name__).warning(f"OTLP exporter initialization failed: {e}")

    # グローバルプロバイダとして設定
    trace.set_tracer_provider(provider)

    # FastAPI 自動計装
    FastAPIInstrumentor().instrument(
        tracer_provider=provider,
        excluded_urls="health,metrics,/healthz,/ready,/live",
    )

    # SQLAlchemy 自動計装
    SQLAlchemyInstrumentor().instrument(
        tracer_provider=provider,
        enable_commenter=True,
        commenter_options={},
    )

    # Redis 自動計装
    RedisInstrumentor().instrument(tracer_provider=provider)

    return provider


def get_tracer(name: str):
    """指定名のトレーサーを取得"""
    return trace.get_tracer(name)


# ===================== 手動スパン作成ヘルパー =====================

from opentelemetry.trace import SpanKind, Status, StatusCode


def create_span(name: str, kind: SpanKind = SpanKind.INTERNAL, attributes: dict = None):
    """手動スパン作成ヘルパー"""
    tracer = get_tracer(__name__)
    span = tracer.start_span(name, kind=kind)
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)
    return span


def record_exception(span, exception: Exception, attributes: dict = None):
    """スパンに例外を記録"""
    span.record_exception(exception, attributes=attributes)
    span.set_status(Status(StatusCode.ERROR, str(exception)))


def set_span_attributes(span, attributes: dict):
    """スパンに属性を一括設定"""
    for key, value in attributes.items():
        span.set_attribute(key, value)
