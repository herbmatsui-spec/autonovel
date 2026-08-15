from __future__ import annotations

from typing import Optional


class GenerationError(Exception):
    """生成系エラーの基底クラス"""

    def __init__(self, message: str, cause: Optional[Exception] = None):
        super().__init__(message)
        self.cause = cause


class LLMTimeoutError(GenerationError):
    pass


class LLMRateLimitError(GenerationError):
    pass


class AuditFailureError(GenerationError):
    pass


class PipelineCancelledError(GenerationError):
    pass
