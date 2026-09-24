"""
writing_service.py - 後方互換性のためのシム。

このモジュールは src.domain.writing.WritingService へのエイリアスとして機能します。
新しいコードでは `from src.domain.writing import WritingService` を使用してください。
"""

import warnings
warnings.warn(
    "src.backend.writing_service は非推奨です。src.domain.writing を使用してください。",
    DeprecationWarning,
    stacklevel=2
)

from src.domain.writing import (
    WritingService,
    WritingGenerationContext,
    clean_writing_response,
)

# 後方互換性のために元のクラス名を維持
__all__ = ["WritingService", "WritingGenerationContext", "clean_writing_response"]