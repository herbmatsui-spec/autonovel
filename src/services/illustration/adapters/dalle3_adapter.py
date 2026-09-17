"""OpenAI DALL-E 3 オンデマンド従量課金アダプタ (v5.0 Step 2).

常駐GPUサーバー不要で、1枚あたり約$0.040（約6円）の従量課金で高品位な挿絵・表紙を生成する。
"""
from __future__ import annotations

import base64
from typing import Optional

import httpx

from src.services.illustration.adapters.base import (
    GeneratedImageResult,
    ImageGenerationAdapter,
    ImagePromptRequest,
)


class Dalle3Adapter(ImageGenerationAdapter):
    """OpenAI DALL-E 3 オンデマンド従量課金アダプタ（標準: $0.040/枚）。"""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self._client = client

    @property
    def provider_name(self) -> str:
        return "dalle3"

    async def generate_image(self, request: ImagePromptRequest) -> GeneratedImageResult:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # DALL-E 3 解像度正規化 (1024x1024, 1792x1024, 1024x1792)
        size = "1024x1024"
        if request.aspect_ratio in ("16:9", "horizontal"):
            size = "1792x1024"
        elif request.aspect_ratio in ("9:16", "vertical"):
            size = "1024x1792"

        payload = {
            "model": "dall-e-3",
            "prompt": request.prompt,
            "n": 1,
            "size": size,
            "response_format": "b64_json",
            "quality": "standard",
        }

        if self._client is not None:
            resp = await self._client.post(
                f"{self.base_url}/images/generations",
                json=payload,
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
        else:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.base_url}/images/generations",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

        b64_str = data["data"][0]["b64_json"]
        image_bytes = base64.b64decode(b64_str)

        return GeneratedImageResult(
            image_bytes=image_bytes,
            format="png",
            provider="dalle3",
            cost_usd=0.040,
            metadata={"revised_prompt": data["data"][0].get("revised_prompt", "")},
        )
