"""
writing_services.py - 後方互換性のためのシム。

このモジュールは src.domain.writing.WritingService へのエイリアスとして機能します。
新しいコードでは `from src.domain.writing import WritingService` を使用してください。
"""

import warnings
warnings.warn(
    "src.services.writing_services は非推奨です。src.domain.writing を使用してください。",
    DeprecationWarning,
    stacklevel=2
)

from src.domain.writing import (
    WritingService,
    WritingServices,
    WritingGenerationContext,
    clean_writing_response,
    StateGuard,
    ValidationResult,
)

# 後方互換性のために元のクラス名を維持（複数形も単数形もエクスポート）
__all__ = [
    "WritingService",
    "WritingServices",
    "WritingGenerationContext",
    "clean_writing_response",
    "StateGuard",
    "ValidationResult",
]