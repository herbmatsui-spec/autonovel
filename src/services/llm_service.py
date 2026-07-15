import logging
from typing import Any, Dict, Optional

from src.llm.model_router import resolve_model, select_model

logger = logging.getLogger(__name__)

_PURPOSES = (
    "planning", "plot_expansion", "writing", "climax",
    "fallback", "ultra_stable", "audit", "marketing",
)


class LLMService:
    """アプリ全体で利用する LLM ラッパー。
    API キーは呼び出し側から渡すか、環境変数 `GEMINI_API_KEY` を使用します。

    Gemini ネイティブモデルは Gemini クライアントへ、OpenAI互換モデル
    (OpenRouter 等の "org/model" 形式や gpt/claude/llama 等) は OpenAI互換
    クライアントへ自動的にルーティングします。
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ""
        if not self.api_key:
            logger.warning("LLMService initialized without API key – calls will fail")
        self._factory: Any = None

    def _resolve_model(self, purpose: str) -> str:
        if purpose in _PURPOSES:
            return select_model(purpose)
        return resolve_model(purpose)

    def _ensure_factory(self) -> Any:
        if self._factory is None:
            from src.backend.engine_utils import AdaptiveCooldown
            from src.core.llm_gateway import LLMProviderFactory, create_genai_client

            genai_client = create_genai_client(self.api_key)
            cooldown = AdaptiveCooldown(base_sec=2.0, min_sec=0.5, max_sec=10.0)
            self._factory = LLMProviderFactory(genai_client, cooldown)
        return self._factory

    async def generate_json(
        self,
        purpose: str,
        prompt: str,
        response_schema: Optional[Any] = None,
        system_instruction: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        model_name = self._resolve_model(purpose)
        client = self._ensure_factory().get_client(model_name)
        metadata, story, _usage = await client.generate_json(
            model_name=model_name,
            prompt=prompt,
            response_schema=response_schema,
            system_instruction=system_instruction,
            temp=kwargs.get("temp", kwargs.get("temperature", 0.7)),
        )
        return {"success": True, "metadata": metadata, "story_content": story}

    async def generate_text(
        self,
        purpose: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        model_name = self._resolve_model(purpose)
        client = self._ensure_factory().get_client(model_name)
        story, _usage = await client.generate_text(
            model_name=model_name,
            prompt=prompt,
            system_instruction=system_instruction,
            temp=kwargs.get("temp", kwargs.get("temperature", 0.7)),
        )
        return str(story)
