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
    return os.getenv("GOOGLE_GENAI_API_KEY", "")


def get_illustration_workflow() -> Any:
    """IllustrationWorkflow を AppContainer 経由で取得する。"""
    container = AppContainer()
    container.api_key.override(_get_api_key())
    return container.illustration_workflow()


_prompt_manager_instance: Any = None


def get_prompt_manager() -> Any:
    """PromptManager の Singleton を返す FastAPI Dependency.

    Router から Depends(get_prompt_manager) で注入可能。
    テスト時は app.dependency_overrides[get_prompt_manager] で差し替え可能。
    """
    global _prompt_manager_instance
    if _prompt_manager_instance is None:
        from prompts.manager import PromptManager

        _prompt_manager_instance = PromptManager()
    return _prompt_manager_instance


__all__ = ["get_illustration_workflow", "get_prompt_manager"]
