# services/llm_service.py
"""LLM 統合サービス (後方互換ラッパー)。

src.services.llm.factory.get_llm_adapter への委譲を提供する。
3レイヤーモデルルータによる用途別最適化も兼ねる。
"""
from __future__ import annotations

import logging
from typing import Any

from src.llm.model_router import resolve_model_for_purpose

logger = logging.getLogger(__name__)


class LLMService:
    """用途別モデル解決とクライアントファクトリへの委譲を提供する LLM 統合サービス。"""

    def __init__(self, llm: Any = None, repo: Any = None, **kwargs: Any):
        self.llm = llm
        self.repo = repo
        self._kwargs = kwargs

    def _ensure_factory(self):
        from src.services.llm.factory import get_llm_adapter

        return self

    def get_client(self, model_name: str | None = None):
        """モデル名から LLM アダプタを取得する。"""
        from src.services.llm.factory import get_llm_adapter

        return get_llm_adapter(model_name=model_name)

    async def generate(self, prompt: str, system_prompt: str | None = None, **kwargs: Any) -> str:
        """プロンプトからテキストを生成する。"""
        from src.services.llm.factory import get_llm_adapter

        adapter = get_llm_adapter(model_name=kwargs.get("model_name"))
        return await adapter.generate_text(
            prompt=prompt, system_prompt=system_prompt or "", max_tokens=kwargs.get("max_tokens", 2000)
        )

    def resolve_model(self, purpose: str, llm_config: dict | None = None, **kwargs: Any) -> str:
        """用途別モデルを解決する (後方互換メソッド)。"""
        return resolve_model_for_purpose(purpose, llm_config or {})


__all__: list[str] = ["LLMService"]
