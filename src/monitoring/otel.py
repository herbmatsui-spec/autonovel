import os
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

def init_otel(app=None, service_name="autonovel"):
    """
    Initialize OpenTelemetry tracing and metrics.
    If app is provided, instruments the FastAPI app.
    """
    # Set up resource
    resource = Resource(attributes={
        "service.name": service_name,
        "service.version": os.environ.get("APP_VERSION", "1.0.0")
    })
    
    # Tracing
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # OTLP exporter for traces
    otlp_trace_endpoint = os.environ.get("OTLP_TRACES_ENDPOINT")
    if otlp_trace_endpoint:
        trace_exporter = OTLPSpanExporter(endpoint=otlp_trace_endpoint, insecure=True)
        span_processor = BatchSpanProcessor(trace_exporter)
        tracer_provider.add_span_processor(span_processor)
    
    # Metrics
    metric_readers = []
    otlp_metric_endpoint = os.environ.get("OTLP_METRICS_ENDPOINT")
    if otlp_metric_endpoint:
        metric_exporter = OTLPMetricExporter(endpoint=otlp_metric_endpoint, insecure=True)
        metric_readers.append(PeriodicExportingMetricReader(metric_exporter))
    
    meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(meter_provider)
    
    # Instrumentations
    FastAPIInstrumentor().instrument_app(app) if app else FastAPIInstrumentor().instrument()
    RequestsInstrumentor().instrument()
    SQLAlchemyInstrumentor().instrument()
    
    return trace.get_tracer(__name__), metrics.get_meter(__name__)