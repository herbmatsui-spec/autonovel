"""
Centralized error handling utilities.

Provides consistent error handling, logging, and response formatting across the application.
"""
import logging
import traceback
from typing import Any, Dict, Optional, Type

from src.core.exceptions import HegemonyError, LLMError, PipelineError

logger = logging.getLogger(__name__)


def handle_exception(
    exc: Exception,
    context: str = "",
    trace_id: Optional[str] = None,
    expected_types: Optional[tuple] = None,
) -> Dict[str, Any]:
    """
    Handle an exception and return a structured error response.

    Args:
        exc: The exception to handle
        context: Context where the error occurred (e.g., "rate_limit_middleware")
        trace_id: Optional trace ID for correlation
        expected_types: Tuple of expected exception types that should not be logged as errors

    Returns:
        Structured error response dict
    """
    # Determine if this is an expected (handled) exception
    is_expected = expected_types and isinstance(exc, expected_types)

    # Build error response
    error_response = {
        "error": type(exc).__name__,
        "message": str(exc),
        "context": context,
    }

    if trace_id:
        error_response["trace_id"] = trace_id

    # Log appropriately
    if isinstance(exc, HegemonyError):
        # Application-level errors are logged at warning level
        logger.warning(
            f"[{context}] {exc.error_code}: {exc.message}",
            extra={"trace_id": trace_id, "error_code": exc.error_code, "status_code": exc.status_code}
        )
        error_response["error_code"] = exc.error_code
        error_response["status_code"] = exc.status_code
    elif is_expected:
        # Expected exceptions (like rate limiting) are debug level
        logger.debug(
            f"[{context}] Expected exception: {exc}",
            extra={"trace_id": trace_id}
        )
    else:
        # Unexpected exceptions are logged as errors with full traceback
        logger.error(
            f"[{context}] Unexpected error: {exc}",
            extra={"trace_id": trace_id},
            exc_info=True
        )
        error_response["error_code"] = "INTERNAL_ERROR"
        error_response["status_code"] = 500

    return error_response


def create_error_response(exc: Exception, trace_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create a standardized error response from an exception.

    Args:
        exc: The exception
        trace_id: Optional trace ID

    Returns:
        Standardized error response dict
    """
    if isinstance(exc, HegemonyError):
        return {
            "error": exc.error_code,
            "message": exc.message,
            "status_code": exc.status_code,
            "trace_id": trace_id,
        }
    elif isinstance(exc, LLMError):
        return {
            "error": "LLM_ERROR",
            "message": str(exc),
            "status_code": 502,
            "trace_id": trace_id,
        }
    elif isinstance(exc, PipelineError):
        return {
            "error": "PIPELINE_ERROR",
            "message": str(exc),
            "status_code": 502,
            "trace_id": trace_id,
        }
    else:
        return {
            "error": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "status_code": 500,
            "trace_id": trace_id,
        }


class ErrorHandler:
    """Context manager for consistent error handling in async functions."""

    def __init__(
        self,
        context: str,
        trace_id: Optional[str] = None,
        expected_types: Optional[tuple] = None,
        reraise: bool = True,
    ):
        self.context = context
        self.trace_id = trace_id
        self.expected_types = expected_types
        self.reraise = reraise
        self.error = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.error = handle_exception(
                exc_val,
                context=self.context,
                trace_id=self.trace_id,
                expected_types=self.expected_types,
            )
            if not self.reraise:
                return True  # Suppress exception
        return False


async def safe_execute(
    coro,
    context: str = "",
    trace_id: Optional[str] = None,
    expected_types: Optional[tuple] = None,
    default_return=None,
):
    """
    Safely execute a coroutine, handling exceptions gracefully.

    Args:
        coro: Coroutine to execute
        context: Context for error logging
        trace_id: Optional trace ID
        expected_types: Expected exception types
        default_return: Value to return on exception (if not reraising)

    Returns:
        Result of coroutine or default_return on exception
    """
    try:
        return await coro
    except Exception as e:
        handle_exception(e, context, trace_id, expected_types)
        return default_return


def format_exception_for_logging(exc: Exception, include_traceback: bool = True) -> str:
    """Format an exception for logging."""
    parts = [f"{type(exc).__name__}: {exc}"]
    if include_traceback:
        parts.append("".join(traceback.format_tb(exc.__traceback__)))
    return "\n".join(parts)