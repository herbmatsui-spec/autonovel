from __future__ import annotations


class GenerationError(Exception):
    """生成系エラーの基底クラス"""

    def __init__(self, message: str, cause: Exception | None = None):
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
