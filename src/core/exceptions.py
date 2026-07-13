"""
src/core/exceptions.py - 覇権AIエンジン統一例外クラス
すべての例外クラスをここに集約し、シンプルで拡張可能なエラー階層を構築する。
"""

from typing import Optional


# Base exception hierarchy
class HegemonyError(Exception):
    """覇権エンジンのすべての例外の基底クラス。
    
    Attributes:
        message: 例外メッセージ
        original: 原因となった元の例外（オプション、追跡に便利）
        recoverable: エラーが復旧可能かどうか（一部のサブクラスで使用）
    """
    def __init__(
        self,
        message: str,
        original: Optional[Exception] = None,
        status_code: int = 500,
        error_code: str = "INTERNAL_ERROR"
    ):
        super().__init__(message)
        self.original = original
        self.message = message
        self.status_code = status_code
        self.error_code = error_code

# LLM関連例外
class LLMError(HegemonyError):
    """LLM処理におけるエラー（API呼び出し、プロンプト、レスポンス処理）。"""
    def __init__(self, message: str, original: Optional[Exception] = None, status_code: int = 500, error_code: str = "LLM_ERROR"):
        super().__init__(message, original, status_code, error_code)

class LLMTemporaryError(LLMError):
    """一時的なLLMエラー（レート制限、一時的サーバー問題、タイムアウト等）。
    リトライ可能なエラー用。
    """
    def __init__(self, message: str, original: Optional[Exception] = None, status_code: int = 503, error_code: str = "LLM_TEMPORARY_ERROR"):
        super().__init__(message, original, status_code, error_code)

class LLMServerError(LLMTemporaryError):
    """LLMサーバー側の一時的なエラー（500 Internal Server Error等）。"""
    def __init__(self, message: str, original: Optional[Exception] = None):
        super().__init__(message, original, 500, "LLM_SERVER_ERROR")

class LLMTimeoutError(LLMTemporaryError):
    """LLM API呼び出しのタイムアウトエラー。"""
    def __init__(self, message: str, original: Optional[Exception] = None):
        super().__init__(message, original, 408, "LLM_TIMEOUT_ERROR")

class LLMRateLimitError(LLMTemporaryError):
    """LLM APIのレート制限エラー。"""
    def __init__(self, message: str, original: Optional[Exception] = None):
        super().__init__(message, original, 429, "LLM_RATE_LIMIT_ERROR")

class LLMUnknownError(LLMError):
    """原因不明のLLMエラー。"""
    pass

class LLMUnrecoverableError(LLMError):
    """復旧不可のLLMエラー（認証失敗、APIキー無効、モデル404等）。
    Fail-Fast目標、エラー即座に伝播。
    """
    pass

class LLMAuthenticationError(LLMUnrecoverableError):
    """LLM API認証エラー。"""
    pass

class LLMTokenLimitError(LLMError):
    """トークン上限超過エラー (Fail-Fast対象)"""
    pass

class LLMValidationError(LLMError):
    """PydanticのバリデーションエラーまたはJSONパース失敗"""
    pass

class LLMInvalidRequestError(LLMUnrecoverableError):
    """LLM APIへの不正なリクエスト（パラメータ不整合、禁止ワード等）。"""
    pass

class LLMContentFilterError(LLMUnrecoverableError):
    """LLMのコンテンツフィルタリングによるブロックエラー。"""
    pass

# アプリ層例外
class AppError(HegemonyError):
    """アプリ層のエラーの基底クラス。
    
    Attributes:
        recoverable: エラーが復旧可能かどうか（通知/UI対応など）。
    """
    def __init__(self, message: str, original: Optional[Exception] = None, recoverable: bool = True, status_code: int = 500, error_code: str = "APP_ERROR"):
        super().__init__(message, original, status_code, error_code)
        self.recoverable = recoverable

class ValidationError(AppError):
    """データバリレーションエラー（入力値チェック、スキーマ検証）。"""
    def __init__(self, message: str, original: Optional[Exception] = None):
        super().__init__(message, original, recoverable=True, status_code=422, error_code="VALIDATION_ERROR")

class NotFoundError(AppError):
    """リソース未検出エラー"""
    def __init__(self, message: str, resource_type: str = "", resource_id: str = ""):
        super().__init__(message, recoverable=False, status_code=404, error_code="NOT_FOUND")
        self.resource_type = resource_type
        self.resource_id = resource_id

class ConflictError(AppError):
    """状態競合エラー"""
    def __init__(self, message: str, original: Optional[Exception] = None):
        super().__init__(message, original, recoverable=True, status_code=409, error_code="CONFLICT")

class StateError(AppError):
    """セッションまたはアプリ状態の不整合エラー（状態矛盾、ロック問題）。"""
    def __init__(self, message: str, original: Optional[Exception] = None):
        super().__init__(message, original, recoverable=True, status_code=400, error_code="STATE_ERROR")

class APIError(AppError):
    """外部API呼び出しエラー（ネットワーク、認証、レスポンス）。"""
    def __init__(self, message: str, original: Optional[Exception] = None):
        super().__init__(message, original, recoverable=True, status_code=502, error_code="API_ERROR")

class EngineError(HegemonyError):
    """API生成に関連する基底例外"""
    def __init__(self, message: str, original: Optional[Exception] = None):
        super().__init__(message, original, status_code=500, error_code="ENGINE_ERROR")

# 後方互換性マップ
COMPAT_MAP = {
    "EngineError": EngineError,
    "APIException": AppError,
}

__all__ = [
    "HegemonyError", "LLMError", "LLMTemporaryError", "LLMRateLimitError", "LLMServerError", "LLMTimeoutError", "LLMUnknownError", "LLMUnrecoverableError", "LLMAuthenticationError", "LLMInvalidRequestError", "LLMContentFilterError",
    "LLMTokenLimitError", "LLMValidationError", "EngineError",
    "AppError", "ValidationError", "NotFoundError", "ConflictError", "StateError", "APIError"
]
