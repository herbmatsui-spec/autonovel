# src/core/exceptions/phase3.py
"""Phase 3 共通例外・エラーコード定義"""
from __future__ import annotations

from typing import Any, Optional


class Phase3Error(Exception):
    """Phase 3 基底例外"""

    def __init__(
        self,
        message: str,
        error_code: str,
        details: Optional[dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> dict:
        """構造化エラー情報を辞書で返す"""
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class CompressionError(Phase3Error):
    """圧縮関連エラー (PHASE3_COMPRESSION_XXX)"""

    def __init__(
        self,
        message: str,
        error_code: str = "PHASE3_COMPRESSION_001",
        details: Optional[dict] = None,
    ):
        code = error_code.removeprefix("PHASE3_COMPRESSION_")
        super().__init__(message, f"PHASE3_COMPRESSION_{code}", details)


class CompressionConfigError(CompressionError):
    """圧縮設定エラー"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "002", details)


class CompressionModelError(CompressionError):
    """圧縮モデル読み込みエラー"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "003", details)


class CompressionCacheError(CompressionError):
    """圧縮キャッシュエラー"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "004", details)


class CompressionLayerError(CompressionError):
    """圧縮層実行エラー"""

    def __init__(self, layer: int, message: str, details: Optional[dict] = None):
        details = details or {}
        details["layer"] = layer
        super().__init__(message, "005", details)


class DAGSchedulerError(Phase3Error):
    """DAGスケジューラ関連エラー (PHASE3_DAG_XXX)"""

    def __init__(
        self,
        message: str,
        error_code: str = "PHASE3_DAG_001",
        details: Optional[dict] = None,
    ):
        code = error_code.removeprefix("PHASE3_DAG_")
        super().__init__(message, f"PHASE3_DAG_{code}", details)


class DAGValidationError(DAGSchedulerError):
    """DAG検証エラー"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "002", details)


class DAGCycleError(DAGSchedulerError):
    """DAGサイクル検出エラー"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "003", details)


class DAGResourceError(DAGSchedulerError):
    """DAGリソース不足エラー"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "004", details)


class DAGTaskError(DAGSchedulerError):
    """DAGタスク実行エラー"""

    def __init__(self, task_id: str, message: str, details: Optional[dict] = None):
        details = details or {}
        details["task_id"] = task_id
        super().__init__(message, "005", details)


class DAGTimeoutError(DAGSchedulerError):
    """DAGタスクタイムアウトエラー"""

    def __init__(self, task_id: str, timeout: float, details: Optional[dict] = None):
        details = details or {}
        details["task_id"] = task_id
        details["timeout"] = timeout
        super().__init__(f"Task {task_id} timed out after {timeout}s", "006", details)


class SocialInteractionError(Phase3Error):
    """ソーシャル相互作用関連エラー (PHASE3_SOCIAL_XXX)"""

    def __init__(
        self,
        message: str,
        error_code: str = "PHASE3_SOCIAL_001",
        details: Optional[dict] = None,
    ):
        code = error_code.removeprefix("PHASE3_SOCIAL_")
        super().__init__(message, f"PHASE3_SOCIAL_{code}", details)


class SocialGenerationError(SocialInteractionError):
    """ソーシャル生成エラー"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "002", details)


class SocialGraphError(SocialInteractionError):
    """ソーシャルグラフ操作エラー"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "003", details)


class SocialSimulationError(SocialInteractionError):
    """ソーシャルシミュレーションエラー"""

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, "004", details)


class ConfigurationError(Phase3Error):
    """設定関連エラー (PHASE3_CONFIG_XXX)"""

    def __init__(
        self,
        message: str,
        error_code: str = "PHASE3_CONFIG_001",
        details: Optional[dict] = None,
    ):
        code = error_code.removeprefix("PHASE3_CONFIG_")
        super().__init__(message, f"PHASE3_CONFIG_{code}", details)


class ResourceExhaustedError(Phase3Error):
    """リソース枯渇エラー (PHASE3_RESOURCE_XXX)"""

    def __init__(
        self,
        message: str,
        error_code: str = "PHASE3_RESOURCE_001",
        details: Optional[dict] = None,
    ):
        code = error_code.removeprefix("PHASE3_RESOURCE_")
        super().__init__(message, f"PHASE3_RESOURCE_{code}", details)