"""OpenTelemetry Setup Module for the Novel Engine.

This module provides complete OpenTelemetry integration for traces, metrics, and logs.
Supports OTLP export over HTTP and gRPC protocols.
"""

import logging
import os
from typing import Optional

from opentelemetry import logs, metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.log_exporter import (
    OTLPLogExporter as OTLPLogExporterHTTP,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter as OTLPMetricExporterHTTP,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as OTLPSpanExporterHTTP,
)
from opentelemetry.sdk.environment_variables import (
    OTEL_DEPLOYMENT_ENVIRONMENT,
    OTEL_EXPORTER_OTLP_ENDPOINT,
    OTEL_SERVICE_NAME,
)
from opentelemetry.sdk.logs import LoggerProvider
from opentelemetry.sdk.logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import DEPLOYMENT_ENVIRONMENT, SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.trace.sampling import AlwaysOnSampler, ParentBased

logger = logging.getLogger(__name__)


class TelemetryConfig:
    """Configuration for OpenTelemetry telemetry collection."""

    def __init__(
        self,
        service_name: Optional[str] = None,
        deployment_env: Optional[str] = None,
        otlp_endpoint: Optional[str] = None,
        use_http: bool = False,
        sampling_ratio: float = 1.0,
        batch_timeout_ms: int = 5000,
        max_queue_size: int = 2048,
        max_export_batch_size: int = 512,
    ):
        self.service_name = service_name or os.getenv(OTEL_SERVICE_NAME, "kaku-hegemony")
        self.deployment_env = deployment_env or os.getenv(OTEL_DEPLOYMENT_ENVIRONMENT, os.getenv("ENVIRONMENT", "development"))
        self.otlp_endpoint = otlp_endpoint or os.getenv(OTEL_EXPORTER_OTLP_ENDPOINT, "http://localhost:4317")
        self.use_http = use_http or os.getenv("OTEL_EXPORTER_OTLP_TRACES_HTTP_ENDPOINT") is not None
        self.sampling_ratio = sampling_ratio
        self.batch_timeout_ms = batch_timeout_ms
        self.max_queue_size = max_queue_size
        self.max_export_batch_size = max_export_batch_size


def init_tracing(config: TelemetryConfig) -> trace.TracerProvider:
    """Initialize OpenTelemetry tracing with OTLP exporter."""
    resource = Resource.create({
        SERVICE_NAME: config.service_name,
        DEPLOYMENT_ENVIRONMENT: config.deployment_env,
    })

    if config.use_http:
        exporter = OTLPSpanExporterHTTP(
            endpoint=f"{config.otlp_endpoint}/v1/traces"
        )
    else:
        exporter = OTLPSpanExporter(
            endpoint=config.otlp_endpoint
        )

    sampler = ParentBased(AlwaysOnSampler() if config.sampling_ratio >= 1.0 else
                           ParentBased(root=AlwaysOnSampler(),
                                        remote=AlwaysOnSampler(),
                                        local=AlwaysOnSampler()))

    provider = TracerProvider(
        resource=resource,
        sampler=sampler
    )

    span_processor = BatchSpanProcessor(
        exporter=exporter,
        batch_timeout=config.batch_timeout_ms,
        max_queue_size=config.max_queue_size,
        max_export_batch_size=config.max_export_batch_size,
    )
    provider.add_span_processor(span_processor)

    trace.set_tracer_provider(provider)

    return provider


def init_metrics(config: TelemetryConfig) -> metrics.MeterProvider:
    """Initialize OpenTelemetry metrics with OTLP exporter."""
    resource = Resource.create({
        SERVICE_NAME: config.service_name,
        DEPLOYMENT_ENVIRONMENT: config.deployment_env,
    })

    if config.use_http:
        exporter = OTLPMetricExporterHTTP(
            endpoint=f"{config.otlp_endpoint}/v1/metrics"
        )
    else:
        exporter = OTLPMetricExporter(
            endpoint=config.otlp_endpoint
        )

    provider = MeterProvider(
        resource=resource,
        metric_readers=[exporter]
    )

    metrics.set_meter_provider(provider)

    return provider


def init_logs(config: TelemetryConfig) -> logs.LoggerProvider:
    """Initialize OpenTelemetry logs with OTLP exporter."""
    resource = Resource.create({
        SERVICE_NAME: config.service_name,
        DEPLOYMENT_ENVIRONMENT: config.deployment_env,
    })

    if config.use_http:
        exporter = OTLPLogExporterHTTP(
            endpoint=f"{config.otlp_endpoint}/v1/logs"
        )
    else:
        exporter = OTLPLogExporter(
            endpoint=config.otlp_endpoint
        )

    log_handler = logs.OtelLogHandler()

    provider = LoggerProvider(resource=resource)
    provider.add_log_record_processor(BatchLogRecordProcessor(exporter))

    logs.set_logger_provider(provider)

    return provider


def setup_telemetry(config: Optional[TelemetryConfig] = None) -> TelemetryConfig:
    """Set up complete OpenTelemetry telemetry stack (traces, metrics, logs)."""
    config = config or TelemetryConfig()

    logging.info(f"Initializing OpenTelemetry for service: {config.service_name}")

    init_tracing(config)
    init_metrics(config)
    init_logs(config)

    logging.info("OpenTelemetry telemetry initialized successfully")

    return config


def get_tracer(name: str = __name__) -> trace.Tracer:
    """Get an OpenTelemetry tracer."""
    return trace.get_tracer(name)


def get_meter(name: str = __name__) -> metrics.Meter:
    """Get an OpenTelemetry meter."""
    return metrics.get_meter(name)


_COST_METRICS = None


def get_cost_metrics() -> "CostMetrics":
    """Get or create cost metrics instance."""
    global _COST_METRICS
    if _COST_METRICS is None:
        _COST_METRICS = CostMetrics()
    return _COST_METRICS


class CostMetrics:
    """Metrics for tracking LLM cost consumption."""

    def __init__(self):
        self._meter = metrics.get_meter("kaku-hegemony.cost")

        self._tokens_input = self._meter.create_counter(
            "llm.tokens.input",
            description="Number of input tokens processed by LLM",
            unit="tokens"
        )

        self._tokens_output = self._meter.create_counter(
            "llm.tokens.output",
            description="Number of output tokens generated by LLM",
            unit="tokens"
        )

        self._cost_usd = self._meter.create_counter(
            "llm.cost.usd",
            description="LLM cost in US dollars",
            unit="USD"
        )

        self._request_count = self._meter.create_counter(
            "llm.requests.total",
            description="Total number of LLM requests",
            unit="requests"
        )

        self._latency_histogram = self._meter.create_histogram(
            "llm.latency.ms",
            description="LLM request latency in milliseconds",
            unit="ms"
        )

    def record_llm_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: float,
        success: bool = True
    ) -> None:
        """Record metrics for an LLM call."""
        self._request_count.add(1, {"model": model, "success": str(success)})
        self._tokens_input.add(input_tokens, {"model": model})
        self._tokens_output.add(output_tokens, {"model": model})
        self._cost_usd.add(cost_usd, {"model": model})
        self._latency_histogram.record(latency_ms, {"model": model})


# Quick setup function for simple use cases
def quick_setup(service_name: str = "kaku-hegemony") -> TelemetryConfig:
    """Quick setup with default configuration."""
    return setup_telemetry(TelemetryConfig(service_name=service_name))
