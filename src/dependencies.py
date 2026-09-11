"""FastAPI 依存性注入 (DI) ヘルパー。

各 router から直接 AppContainer を触らず、本モジュール経由で
必要なサービス / ワークフローを取得する。

- Issue #6 (挿絵) 対応: ``get_illustration_workflow`` を提供し、
  router 内で未 import だった AppContainer のバグを解消。
- 将来他の DI もここに集約する。
"""

from __future__ import annotations

import os
from typing import Any

from src.core.container import AppContainer


def _get_api_key() -> str:
    from src.backend.config import settings
    # Use centralized settings for GEMINI_API_KEY or GOOGLE_GENAI_API_KEY
    key = settings.GEMINI_API_KEY
    if not key:
        import os
        key = os.getenv("GOOGLE_GENAI_API_KEY") or os.getenv("GEMINI_API_KEY")
    return key or ""


def get_illustration_workflow() -> Any:
    """IllustrationWorkflow を AppContainer 経由で取得する。"""
    container = AppContainer()
    container.api_key.override(_get_api_key())
    return container.illustration_workflow()


def get_prompt_manager() -> Any:
    """PromptManager の Singleton を返す FastAPI Dependency.

    AppContainer の pm プロバイダを経由して取得する。
    Router から Depends(get_prompt_manager) で注入可能。
    テスト時は app.dependency_overrides[get_prompt_manager] で差し替え可能。
    """
    return AppContainer.pm()


__all__ = ["get_illustration_workflow", "get_prompt_manager"]
