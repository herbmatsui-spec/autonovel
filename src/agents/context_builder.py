"""
context_builder.py - 執筆コンテキスト構築ユーティリティ (非推奨)

このモジュールは非推奨です。新しいコードでは `src.agents.context_builder_agent.ContextBuilderAgent` を使用してください。
"""

from __future__ import annotations
import warnings
from src.agents.context_builder_agent import ContextBuilderAgent

# 後方互換性エイリアスとして残し、警告のみを出す
class ContextBuilder(ContextBuilderAgent):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "ContextBuilder is deprecated. Use ContextBuilderAgent instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(*args, **kwargs)
