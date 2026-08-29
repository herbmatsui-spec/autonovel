"""Backend error utilities for structured TaskError handling.

Provides a helper to create a consistent ``TaskErrorDetail`` object
(defined in ``src.models.api_schemas.TaskErrorDetail``) from various
exception types and manual error conditions.
"""

from datetime import datetime
import logging
from typing import Any, Dict, Optional

from src.core.observability import TraceContext
from src.models.api_schemas import TaskErrorDetail


def log_exception(
    logger: logging.Logger,
    msg: str,
    exc: BaseException,
    *args,
) -> None:
    """trace_id を自動付与して例外をログ出力"""
    trace_id = TraceContext.get_trace_id()
    extra = {"trace_id": trace_id} if trace_id else {}
    logger.error("%s: %s", msg, exc, exc_info=exc, extra=extra, *args)


# ---------------------------------------------------------------------------
# Helper to build a TaskErrorDetail from explicit arguments.
# ---------------------------------------------------------------------------

def create_task_error(
    code: str,
    message: str,
    detail: Optional[str] = None,
    exception: Optional[BaseException] = None,
    retry_after_ms: Optional[int] = None,
    recoverable: bool = True,
    context: Optional[Dict[str, Any]] = None,
) -> TaskErrorDetail:
    """Create a ``TaskErrorDetail`` instance.

    Parameters
    ----------
    code:
        Machine‑readable error identifier (e.g. ``NETWORK_ERROR``).
    message:
        User‑facing short message.
    detail:
        Optional technical description or stack trace.
    exception:
        Optional caught exception – its ``str`` representation will be added
        to ``detail`` if ``detail`` is not supplied.
    retry_after_ms:
        Milliseconds the client should wait before retrying (used for
        rate‑limit errors).
    recoverable:
        Indicates whether the client can retry or resume the task.
    context:
        Arbitrary key‑value pairs with additional debugging information.
    """
    if detail is None and exception is not None:
        detail = str(exception)
    return TaskErrorDetail(
        code=code,
        message=message,
        detail=detail,
        timestamp=datetime.utcnow(),
        retry_after_ms=retry_after_ms,
        recoverable=recoverable,
        context=context or {},
    )

# ---------------------------------------------------------------------------
# Classification of generic exceptions into structured TaskErrorDetail.
# ---------------------------------------------------------------------------

def classify_exception(exc: BaseException) -> TaskErrorDetail:
    """Map a caught exception to a ``TaskErrorDetail``.

    The mapping is intentionally simple – more specific exception types can be
    added later.  This function ensures that *any* unexpected exception still
    yields a well‑formed error object for the frontend.
    """
    # Example custom exception classes (they may already exist in the codebase)
    # from src.backend.exceptions import RateLimitError, ValidationError, LLMError
    # For now we fall back to string matching heuristics.
    exc_str = str(exc).lower()
    if "rate limit" in exc_str:
        return create_task_error(
            code="API_LIMIT",
            message="API 呼び出し回数が上限に達しました",
            detail=str(exc),
            retry_after_ms=5000,  # default 5 seconds
            recoverable=True,
            context={"exception_type": exc.__class__.__name__},
        )
    if "validation" in exc_str:
        return create_task_error(
            code="VALIDATION_ERROR",
            message="リクエストが無効です",
            detail=str(exc),
            recoverable=False,
            context={"exception_type": exc.__class__.__name__},
        )
    if "llm" in exc_str or "openai" in exc_str:
        return create_task_error(
            code="LLM_ERROR",
            message="AI 呼び出しでエラーが発生しました",
            detail=str(exc),
            recoverable=True,
            context={"exception_type": exc.__class__.__name__},
        )
    # Fallback generic error
    return create_task_error(
        code="UNKNOWN",
        message="内部エラーが発生しました",
        detail=str(exc),
        recoverable=False,
        context={"exception_type": exc.__class__.__name__},
    )
