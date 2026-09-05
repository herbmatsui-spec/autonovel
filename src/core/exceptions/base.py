"""AutoNovel 基底例外定義モジュール。

アプリケーション全体で利用される基本例外クラス群を提供する。
"""

from __future__ import annotations


class HegemonyError(Exception):
    """基底例外クラス。全サブクラスが status_code, error_code, message, original を提供する。"""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str
    original: Exception | None = None

    def __init__(
        self,
        message: str = "",
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR",
        original: Exception | None = None,
        **kwargs,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.original = original
        super().__init__(message)


class EngineError(HegemonyError):
    """エンジン固有エラー"""

    def __init__(
        self,
        message: str = "",
        status_code: int = 500,
        error_code: str = "ENGINE_ERROR",
        original: Exception | None = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class LLMError(HegemonyError):
    """LLM呼び出しエラー"""

    def __init__(
        self,
        message: str = "",
        status_code: int = 502,
        error_code: str = "LLM_ERROR",
        original: Exception | None = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class LLMTemporaryError(LLMError):
    """一時的なLLMエラー（レート制限等）"""

    def __init__(
        self,
        message: str = "",
        status_code: int = 429,
        error_code: str = "LLM_TEMPORARY_ERROR",
        original: Exception | None = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class LLMTokenLimitError(LLMError):
    """トークン制限エラー"""

    def __init__(
        self,
        message: str = "",
        status_code: int = 400,
        error_code: str = "LLM_TOKEN_LIMIT_ERROR",
        original: Exception | None = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class LLMValidationError(LLMError):
    """レスポンス検証エラー"""

    def __init__(
        self,
        message: str = "",
        status_code: int = 422,
        error_code: str = "LLM_VALIDATION_ERROR",
        original: Exception | None = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class LLMUnrecoverableError(LLMError):
    """回復不可能なLLMエラー"""

    def __init__(
        self,
        message: str = "",
        status_code: int = 502,
        error_code: str = "LLM_UNRECOVERABLE_ERROR",
        original: Exception | None = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class APIError(HegemonyError):
    """API呼び出しエラー"""

    def __init__(
        self,
        message: str = "",
        status_code: int = 502,
        error_code: str = "API_ERROR",
        original: Exception | None = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class AppError(HegemonyError):
    """アプリケーションエラー"""

    def __init__(
        self,
        message: str = "",
        status_code: int = 500,
        error_code: str = "APP_ERROR",
        original: Exception | None = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class ValidationError(HegemonyError):
    """バリデーションエラー"""

    def __init__(
        self,
        message: str = "",
        status_code: int = 422,
        error_code: str = "VALIDATION_ERROR",
        original: Exception | None = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class NotFoundError(HegemonyError):
    """リソース未検出エラー"""

    def __init__(
        self,
        message: str = "",
        status_code: int = 404,
        error_code: str = "NOT_FOUND",
        original: Exception | None = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


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
        original: Exception | None = None,
        status_code: int = 502,
        error_code: str = "COMMERCIAL_PIPELINE_ERROR",
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


# ----------------------------------------------------------------------
# LLM 系統固有例外（プロバイダー側でインポートされる）
# ----------------------------------------------------------------------


class LLMAuthenticationError(LLMError):
    """認証失敗（API キーが無効・期限切れなど）"""


class LLMContentFilterError(LLMError):
    """コンテンツフィルタに引っかかった場合"""


class LLMInvalidRequestError(LLMError):
    """リクエストパラメータが不正なとき"""


class LLMRateLimitError(LLMTemporaryError):
    """レートリミット・クオータ超過（一時的エラー）"""


class LLMServerError(LLMError):
    """サーバ側エラー（5xx 系）"""


class LLMTimeoutError(LLMError):
    """API 呼び出しがタイムアウトしたとき"""


class LLMUnknownError(LLMError):
    """上記に該当しない未知のエラー"""
