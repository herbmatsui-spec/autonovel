from typing import Dict

from google import genai

from src.backend.engine_utils import AdaptiveCooldown
from src.llm.base import LLMProvider
from src.llm.gemini_provider import GeminiProvider
from src.llm.openai_provider import OpenAIProvider


class LLMProviderFactory:
    """
    モデル名に基づいて適切な LLMProvider を提供するファクトリクラス。
    依存性の注入 (DI) を容易にし、アプリケーション層を特定の SDK から切り離す。
    """
    def __init__(self, genai_client: genai.Client, cooldown: AdaptiveCooldown):
        # プロバイダーのインスタンス化
        self._providers: Dict[str, LLMProvider] = {
            "gemini": GeminiProvider(genai_client, cooldown),
            "openai": OpenAIProvider(cooldown),
        }

    def get_provider(self, model_name: str) -> LLMProvider:
        """
        モデル名から最適なプロバイダーを選択して返す。
        """
        model_lower = model_name.lower()

        # OpenAI互換 (GPT, Claude-via-OpenRouter, Llama etc.)
        if any(x in model_lower for x in ["gpt", "claude", "llama", "mistral", "qwen"]):
            return self._providers["openai"]

        # デフォルトは Gemini
        return self._providers["gemini"]

    def get_all_providers(self) -> Dict[str, LLMProvider]:
        return self._providers
