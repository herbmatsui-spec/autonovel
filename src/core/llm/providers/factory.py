from typing import Dict

from google import genai

from src.backend.engine_utils import AdaptiveCooldown
from src.core.llm.providers.base import LLMProvider
from src.core.llm.providers.gemini import GeminiProvider
from src.core.llm.providers.openai import OpenAIProvider
from src.core.llm.router import is_openai_compatible


class LLMProviderFactory:
    def __init__(self, genai_client: genai.Client, cooldown: AdaptiveCooldown):
        self._providers: Dict[str, LLMProvider] = {
            "gemini": GeminiProvider(genai_client, cooldown),
            "openai": OpenAIProvider(cooldown),
        }

    def get_provider(self, model_name: str) -> LLMProvider:
        if is_openai_compatible(model_name):
            return self._providers["openai"]
        return self._providers["gemini"]

    def get_all_providers(self) -> Dict[str, LLMProvider]:
        return self._providers
