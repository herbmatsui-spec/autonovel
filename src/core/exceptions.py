from typing import Optional

class HegemonyError(Exception):
    """基底例外クラス"""
    def __init__(self, message: str = "", *args, **kwargs):
        super().__init__(message, *args, **kwargs)

class EngineError(HegemonyError):
    """エンジン固有エラー"""
    pass

class LLMError(HegemonyError):
    """LLM呼び出しエラー"""
    pass

class LLMTemporaryError(LLMError):
    """一時的なLLMエラー（レート制限等）"""
    pass

class LLMTokenLimitError(LLMError):
    """トークン制限エラー"""
    pass

class LLMValidationError(LLMError):
    """レスポンス検証エラー"""
    pass

class LLMUnrecoverableError(LLMError):
    """回復不可能なLLMエラー"""
    pass

class APIError(HegemonyError):
    """API呼び出しエラー"""
    pass

class AppError(HegemonyError):
    """アプリケーションエラー"""
    pass

class ValidationError(HegemonyError):
    """バリデーションエラー"""
    pass

class NotFoundError(HegemonyError):
    """リソース未検出エラー"""
    pass

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
        error_code: str = "COMMERCIAL_PIPELINE_ERROR"
    ):
        super().__init__(message, original, status_code, error_code)
