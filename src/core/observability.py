"""Structured logging utilities for the novel engine."""
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, Optional


class TraceContext:
    """Trace context for request correlation."""
    _current_trace_id: Optional[str] = None

    @classmethod
    def get_trace_id(cls) -> str:
        if cls._current_trace_id is None:
            cls._current_trace_id = str(uuid.uuid4())
        return cls._current_trace_id

    @classmethod
    def set_trace_id(cls, trace_id: str):
        cls._current_trace_id = trace_id

    @classmethod
    def clear(cls):
        cls._current_trace_id = None

class TraceIdFilter(logging.Filter):
    """Logging filter that adds trace ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = TraceContext.get_trace_id()
        return True

class StructuredLogger(logging.LoggerAdapter):
    """Structured logger with trace_id support."""

    def __init__(self, name: str):
        super().__init__(logging.getLogger(name), {})

    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        kwargs.setdefault('extra', {})
        kwargs['extra'].setdefault('trace_id', TraceContext.get_trace_id())
        kwargs['extra'].setdefault('timestamp', datetime.now().isoformat())
        return msg, kwargs

def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger with trace_id support."""
    return StructuredLogger(name)

def with_trace_context(func):
    """Trace context decorator stub."""
    return func

def track_llm_call(func):
    """LLM call tracking decorator stub."""
    return func
