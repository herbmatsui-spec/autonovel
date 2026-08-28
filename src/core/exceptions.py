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

    def __init__(
        self,
        message: str = "",
        status_code: int = 500,
        error_code: str = "ENGINE_ERROR",
        original: Optional[Exception] = None,
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
        original: Optional[Exception] = None,
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
        original: Optional[Exception] = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class LLMAuthenticationError(LLMError):
    """認証エラー（APIキーやトークンが無効）"""

    def __init__(
        self,
        message: str = "",
        status_code: int = 401,
        error_code: str = "LLM_AUTHENTICATION_ERROR",
        original: Optional[Exception] = None,
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
        original: Optional[Exception] = None,
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
        original: Optional[Exception] = None,
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
        original: Optional[Exception] = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class LLMContentFilterError(LLMError):
    """コンテンツフィルターによる遮断エラー"""

    def __init__(
        self,
        message: str = "",
        original: Optional[Exception] = None,
        status_code: int = 400,
        error_code: str = "LLM_CONTENT_FILTER_ERROR",
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class LLMInvalidRequestError(LLMError):
    """無効なリクエストエラー"""

    def __init__(
        self,
        message: str = "",
        original: Optional[Exception] = None,
        status_code: int = 400,
        error_code: str = "LLM_INVALID_REQUEST_ERROR",
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class LLMRateLimitError(LLMTemporaryError):
    """レート制限エラー"""

    def __init__(
        self,
        message: str = "",
        original: Optional[Exception] = None,
        status_code: int = 429,
        error_code: str = "LLM_RATE_LIMIT_ERROR",
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class LLMServerError(LLMError):
    """LLMサーバー側エラー"""

    def __init__(
        self,
        message: str = "",
        original: Optional[Exception] = None,
        status_code: int = 500,
        error_code: str = "LLM_SERVER_ERROR",
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class LLMTimeoutError(LLMTemporaryError):
    """タイムアウトエラー"""

    def __init__(
        self,
        message: str = "",
        original: Optional[Exception] = None,
        status_code: int = 504,
        error_code: str = "LLM_TIMEOUT_ERROR",
        **kwargs,
    ):
        super().__init__(
            message=message,
            status_code=status_code,
            error_code=error_code,
            original=original,
            **kwargs,
        )


class LLMUnknownError(LLMError):
    """未知のLLMエラー"""

    def __init__(
        self,
        message: str = "",
        original: Optional[Exception] = None,
        status_code: int = 500,
        error_code: str = "LLM_UNKNOWN_ERROR",
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
        original: Optional[Exception] = None,
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
        original: Optional[Exception] = None,
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
        original: Optional[Exception] = None,
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
        original: Optional[Exception] = None,
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
        original: Optional[Exception] = None,
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


class BibleGenerationError(PipelineError):
    """Bible生成エラー"""

    def __init__(
        self,
        message: str = "Bible generation failed",
        original: Optional[Exception] = None,
        fallback_used: bool = False,
        **kwargs,
    ):
        super().__init__(
            message=message,
            original=original,
            status_code=502,
            error_code="BIBLE_GENERATION_ERROR",
            **kwargs,
        )
        self.fallback_used = fallback_used


class EpisodeWritingError(PipelineError):
    """エピソード執筆エラー"""

    def __init__(
        self,
        message: str = "Episode writing failed",
        original: Optional[Exception] = None,
        episode_num: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            original=original,
            status_code=502,
            error_code="EPISODE_WRITING_ERROR",
            **kwargs,
        )
        self.episode_num = episode_num


class EpisodeAuditError(PipelineError):
    """エピソード監査エラー"""

    def __init__(
        self,
        message: str = "Episode audit failed",
        original: Optional[Exception] = None,
        episode_num: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            original=original,
            status_code=502,
            error_code="EPISODE_AUDIT_ERROR",
            **kwargs,
        )
        self.episode_num = episode_num


class EpisodeRewriteError(PipelineError):
    """エピソードリライトエラー"""

    def __init__(
        self,
        message: str = "Episode rewrite failed",
        original: Optional[Exception] = None,
        episode_num: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            original=original,
            status_code=502,
            error_code="EPISODE_REWRITE_ERROR",
            **kwargs,
        )
        self.episode_num = episode_num


class PlotGenerationError(PipelineError):
    """プロット生成エラー"""

    def __init__(
        self,
        message: str = "Plot generation failed",
        original: Optional[Exception] = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            original=original,
            status_code=502,
            error_code="PLOT_GENERATION_ERROR",
            **kwargs,
        )


class SeriesFinalizationError(PipelineError):
    """シリーズ完結処理エラー"""

    def __init__(
        self,
        message: str = "Series finalization failed",
        original: Optional[Exception] = None,
        **kwargs,
    ):
        super().__init__(
            message=message,
            original=original,
            status_code=502,
            error_code="SERIES_FINALIZATION_ERROR",
            **kwargs,
        )
