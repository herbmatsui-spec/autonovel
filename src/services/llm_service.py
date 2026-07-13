import logging
from typing import Any, Dict, Optional

from src.llm.gemini_client import GeminiClient
from src.llm.model_router import select_model

logger = logging.getLogger(__name__)

class LLMService:
    """アプリ全体で利用する LLM ラッパー。
    API キーは呼び出し側から渡すか、環境変数 `GEMINI_API_KEY` を使用します。
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or ""
        if not self.api_key:
            logger.warning("LLMService initialized without API key – calls will fail")
        self._client: Optional[GeminiClient] = None

    def _ensure_client(self) -> GeminiClient:
        if self._client is None:
            self._client = GeminiClient(api_key=self.api_key)
        return self._client

    async def generate_json(
        self,
        purpose: str,
        prompt: str,
        response_schema: Optional[Any] = None,
        system_instruction: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        model_name = select_model(purpose)
        client = self._ensure_client()
        return await client.generate_json(
            model_name=model_name,
            prompt=prompt,
            response_schema=response_schema,
            system_instruction=system_instruction,
            **kwargs,
        )

    async def generate_text(
        self,
        purpose: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        model_name = select_model(purpose)
        client = self._ensure_client()
        return await client.generate_text(
            model_name=model_name,
            prompt=prompt,
            system_instruction=system_instruction,
            **kwargs,
        )
