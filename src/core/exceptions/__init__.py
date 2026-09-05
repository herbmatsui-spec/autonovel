# src/core/exceptions/__init__.py
"""例外モジュール"""
# 元の例外 (src/core/exceptions.py からインポート)
import sys
import importlib.util

# src/core/exceptions.py を直接インポート
spec = importlib.util.spec_from_file_location(
    "core_exceptions", 
    "/home/herbmatsui/autonovel/src/core/exceptions.py"
)
core_exceptions = importlib.util.module_from_spec(spec)
sys.modules["core_exceptions"] = core_exceptions
spec.loader.exec_module(core_exceptions)

# 元の例外をエクスポート
HegemonyError = core_exceptions.HegemonyError
EngineError = core_exceptions.EngineError
LLMError = core_exceptions.LLMError
LLMTemporaryError = core_exceptions.LLMTemporaryError
LLMTokenLimitError = core_exceptions.LLMTokenLimitError
LLMValidationError = core_exceptions.LLMValidationError
LLMUnrecoverableError = core_exceptions.LLMUnrecoverableError
APIError = core_exceptions.APIError
AppError = core_exceptions.AppError
ValidationError = core_exceptions.ValidationError
NotFoundError = core_exceptions.NotFoundError
PipelineError = core_exceptions.PipelineError
LLMAuthenticationError = core_exceptions.LLMAuthenticationError
LLMContentFilterError = core_exceptions.LLMContentFilterError
LLMInvalidRequestError = core_exceptions.LLMInvalidRequestError
LLMRateLimitError = core_exceptions.LLMRateLimitError
LLMServerError = core_exceptions.LLMServerError
LLMTimeoutError = core_exceptions.LLMTimeoutError
LLMUnknownError = core_exceptions.LLMUnknownError

# Phase 3 例外
from .phase3 import (
    Phase3Error,
    CompressionError,
    CompressionConfigError,
    CompressionModelError,
    CompressionCacheError,
    CompressionLayerError,
    DAGSchedulerError,
    DAGValidationError,
    DAGCycleError,
    DAGResourceError,
    DAGTaskError,
    DAGTimeoutError,
    SocialInteractionError,
    SocialGenerationError,
    SocialGraphError,
    SocialSimulationError,
    ConfigurationError,
    ResourceExhaustedError,
)

__all__ = [
    # 元の例外
    "HegemonyError",
    "EngineError",
    "LLMError",
    "LLMTemporaryError",
    "LLMTokenLimitError",
    "LLMValidationError",
    "LLMUnrecoverableError",
    "APIError",
    "AppError",
    "ValidationError",
    "NotFoundError",
    "PipelineError",
    "LLMAuthenticationError",
    "LLMContentFilterError",
    "LLMInvalidRequestError",
    "LLMRateLimitError",
    "LLMServerError",
    "LLMTimeoutError",
    "LLMUnknownError",
    # Phase 3 例外
    "Phase3Error",
    "CompressionError",
    "CompressionConfigError",
    "CompressionModelError",
    "CompressionCacheError",
    "CompressionLayerError",
    "DAGSchedulerError",
    "DAGValidationError",
    "DAGCycleError",
    "DAGResourceError",
    "DAGTaskError",
    "DAGTimeoutError",
    "SocialInteractionError",
    "SocialGenerationError",
    "SocialGraphError",
    "SocialSimulationError",
    "ConfigurationError",
    "ResourceExhaustedError",
]