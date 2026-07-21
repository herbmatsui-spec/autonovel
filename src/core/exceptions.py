from typing import Optional

class HegemonyError(Exception):
    """基底例外クラス。全サブクラスが status_code, error_code, message, original を提供する。"""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str
    original: Optional[Exception] = None

    def __init__(
        self,
        message: str = "",
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        original: Optional[Exception] = None,
        **kwargs,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.original = original
        super().__init__(message, **kwargs)

class EngineError(HegemonyError):
    """エンジン固有エラー"""
    def __init__(self, message: str = "", status_code: int = 500, error_code: str = "ENGINE_ERROR", original: Optional[Exception] = None, **kwargs):
        super().__init__(message=message, status_code=status_code, error_code=error_code, original=original, **kwargs)

class LLMError(HegemonyError):
    """LLM呼び出しエラー"""
    def __init__(self, message: str = "", status_code: int = 502, error_code: str = "LLM_ERROR", original: Optional[Exception] = None, **kwargs):
        super().__init__(message=message, status_code=status_code, error_code=error_code, original=original, **kwargs)

class LLMTemporaryError(LLMError):
    """一時的なLLMエラー（レート制限等）"""
    def __init__(self, message: str = "", status_code: int = 429, error_code: str = "LLM_TEMPORARY_ERROR", original: Optional[Exception] = None, **kwargs):
        super().__init__(message=message, status_code=status_code, error_code=error_code, original=original, **kwargs)

class LLMTokenLimitError(LLMError):
    """トークン制限エラー"""
    def __init__(self, message: str = "", status_code: int = 400, error_code: str = "LLM_TOKEN_LIMIT_ERROR", original: Optional[Exception] = None, **kwargs):
        super().__init__(message=message, status_code=status_code, error_code=error_code, original=original, **kwargs)

class LLMValidationError(LLMError):
    """レスポンス検証エラー"""
    def __init__(self, message: str = "", status_code: int = 422, error_code: str = "LLM_VALIDATION_ERROR", original: Optional[Exception] = None, **kwargs):
        super().__init__(message=message, status_code=status_code, error_code=error_code, original=original, **kwargs)

class LLMUnrecoverableError(LLMError):
    """回復不可能なLLMエラー"""
    def __init__(self, message: str = "", status_code: int = 502, error_code: str = "LLM_UNRECOVERABLE_ERROR", original: Optional[Exception] = None, **kwargs):
        super().__init__(message=message, status_code=status_code, error_code=error_code, original=original, **kwargs)

class APIError(HegemonyError):
    """API呼び出しエラー"""
    def __init__(self, message: str = "", status_code: int = 502, error_code: str = "API_ERROR", original: Optional[Exception] = None, **kwargs):
        super().__init__(message=message, status_code=status_code, error_code=error_code, original=original, **kwargs)

class AppError(HegemonyError):
    """アプリケーションエラー"""
    def __init__(self, message: str = "", status_code: int = 500, error_code: str = "APP_ERROR", original: Optional[Exception] = None, **kwargs):
        super().__init__(message=message, status_code=status_code, error_code=error_code, original=original, **kwargs)

class ValidationError(HegemonyError):
    """バリデーションエラー"""
    def __init__(self, message: str = "", status_code: int = 422, error_code: str = "VALIDATION_ERROR", original: Optional[Exception] = None, **kwargs):
        super().__init__(message=message, status_code=status_code, error_code=error_code, original=original, **kwargs)

class NotFoundError(HegemonyError):
    """リソース未検出エラー"""
    def __init__(self, message: str = "", status_code: int = 404, error_code: str = "NOT_FOUND", original: Optional[Exception] = None, **kwargs):
        super().__init__(message=message, status_code=status_code, error_code=error_code, original=original, **kwargs)

class PipelineError(HegemonyError):
    """商用パイプライン固有エラー。

    Attributes:
        message: エラー メッセージ
        status_code: HTTP ステータスコード (デフォルト 502)
        error_code: エラー コード (デフォルト "COMMERCIAL_PIPELINE_ERROR")
    """
    def __init__(
        self,
        message: str,
        original: Optional[Exception] = None,
        status_code: int = 502,
        error_code: str = "COMMERCIAL_PIPELINE_ERROR",
        **kwargs,
    ):
        super().__init__(message=message, status_code=status_code, error_code=error_code, original=original, **kwargs)
