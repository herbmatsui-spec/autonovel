import json
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

class GeminiClient:
    """Gemini API ラッパークラス。
    JSON 出力やテキスト出力を非同期で取得できるシンプルなインターフェースを提供する。
    """

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta9/models"

    def __init__(self, api_key: str, timeout: float = 10.0):
        self.api_key = api_key
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=self.timeout)

    async def _post(self, model: str, payload: Dict[str, Any]) -> httpx.Response:
        url = f"{self.BASE_URL}/{model}:generateContent"
        params = {"key": self.api_key}
        try:
            resp = await self._client.post(url, params=params, json=payload)
            resp.raise_for_status()
            return resp
        except httpx.HTTPError as exc:
            logger.error(f"Gemini request failed: {exc}")
            raise

    async def generate_json(
        self,
        model_name: str,
        prompt: str,
        response_schema: Optional[Any] = None,
        system_instruction: Optional[str] = None,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Gemini へテキストプロンプトを送り、JSON 形式で結果を取得する。
        `response_schema` が渡された場合は Pydantic の `model_validate` で検証し、
        `data` キーに結果を格納した dict を返す。
        """
        payload: Dict[str, Any] = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        # 追加オプションはそのまま payload にマージ（例: temperature）
        payload.update(kwargs)
        resp = await self._post(model_name, payload)
        result = resp.json()
        # Gemini の応答は `candidates[0].content.parts[0].text` に生成テキストが入る
        try:
            text = result["candidates"][0]["content"]["parts"][0]["text"]
            data = json.loads(text)
        except Exception as exc:
            logger.error(f"Failed to parse Gemini JSON response: {exc}")
            raise
        if response_schema:
            # Pydantic model で検証する（バリデーションエラーはそのまま上位へ）
            data = response_schema.model_validate(data)
        return {"success": True, "metadata": data}

    async def generate_text(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """テキスト生成のみを行うシンプルラッパー。"""
        payload: Dict[str, Any] = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}
        if system_instruction:
            payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}
        payload.update(kwargs)
        resp = await self._post(model_name, payload)
        try:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:
            logger.error(f"Failed to extract text from Gemini response: {exc}")
            raise
