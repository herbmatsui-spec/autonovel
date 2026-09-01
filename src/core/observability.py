"""Structured logging utilities for the novel engine."""

import contextvars
import logging
import uuid
from datetime import datetime
from typing import Any


class TraceContext:
    """Trace context for request correlation."""

    _current_trace_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
        "_current_trace_id", default=None
    )

    @classmethod
    def get_trace_id(cls) -> str:
        trace_id = cls._current_trace_id.get()
        if trace_id is None:
            trace_id = str(uuid.uuid4())
            cls._current_trace_id.set(trace_id)
        return trace_id

    @classmethod
    def set_trace_id(cls, trace_id: str):
        cls._current_trace_id.set(trace_id)

    @classmethod
    def clear(cls):
        cls._current_trace_id.set(None)


class TraceIdFilter(logging.Filter):
    """Logging filter that adds trace ID to log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = TraceContext.get_trace_id()
        return True


class StructuredLogger(logging.LoggerAdapter):
    """Structured logger with trace_id support."""

    def __init__(self, name: str):
        super().__init__(logging.getLogger(name), {})

    def process(self, msg: str, kwargs: dict[str, Any]) -> tuple:
        # Extract special kwargs that should not go into extra
        special_keys = {"exc_info", "stack_info", "stacklevel", "extra"}
        # Get user-provided extra dict or create empty one
        extra = kwargs.get("extra", {}).copy()
        # Add all non-special kwargs to extra
        for key, value in list(kwargs.items()):
            if key not in special_keys:
                extra[key] = value
                del kwargs[key]
        # Ensure we have an extra dict
        kwargs["extra"] = extra
        # Add standard fields
        kwargs["extra"].setdefault("trace_id", TraceContext.get_trace_id())
        kwargs["extra"].setdefault("timestamp", datetime.now().isoformat())
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
