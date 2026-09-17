"""fal.ai (Flux.1 / SDXL) 高速・格安オンデマンド画像生成APIアダプタ (v5.0 Step 3).

Flux.1 schnell (約$0.003/枚 ≒ 約0.45円) や SDXL (約$0.005/枚 ≒ 約0.75円) を利用し、
自前GPUサーバー不要で超高速・高品位な挿絵生成を実現する。
"""
from __future__ import annotations

from typing import Optional

import httpx

from src.services.illustration.adapters.base import (
    GeneratedImageResult,
    ImageGenerationAdapter,
    ImagePromptRequest,
)


class FalAiAdapter(ImageGenerationAdapter):
    """fal.ai 従量課金アダプタ（Flux.1 schnell: 約$0.003/枚, SDXL: 約$0.005/枚）。"""

    def __init__(
        self,
        api_key: str,
        model_endpoint: str = "fal-ai/flux/schnell",
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.api_key = api_key
        self.model_endpoint = model_endpoint
        self._client = client

    @property
    def provider_name(self) -> str:
        return "fal_ai"

    async def generate_image(self, request: ImagePromptRequest) -> GeneratedImageResult:
        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json",
        }

        image_size = "square_hd"
        if request.aspect_ratio in ("9:16", "vertical"):
            image_size = "portrait_16_9"
        elif request.aspect_ratio in ("16:9", "horizontal"):
            image_size = "landscape_16_9"

        payload = {
            "prompt": request.prompt,
            "image_size": image_size,
            "num_inference_steps": (
                min(request.steps, 10) if "schnell" in self.model_endpoint else request.steps
            ),
            "seed": request.seed,
            "enable_safety_checker": True,
        }

        if self._client is not None:
            submit_resp = await self._client.post(
                f"https://queue.fal.run/{self.model_endpoint}",
                json=payload,
                headers=headers,
            )
            submit_resp.raise_for_status()
            data = submit_resp.json()

            image_url = data["images"][0]["url"]
            img_resp = await self._client.get(image_url)
            img_resp.raise_for_status()
            image_bytes = img_resp.content
        else:
            async with httpx.AsyncClient(timeout=45.0) as client:
                submit_resp = await client.post(
                    f"https://queue.fal.run/{self.model_endpoint}",
                    json=payload,
                    headers=headers,
                )
                submit_resp.raise_for_status()
                data = submit_resp.json()

                image_url = data["images"][0]["url"]
                img_resp = await client.get(image_url)
                img_resp.raise_for_status()
                image_bytes = img_resp.content

        return GeneratedImageResult(
            image_bytes=image_bytes,
            format="png",
            provider="fal_ai",
            cost_usd=0.0035,
            metadata={"endpoint": self.model_endpoint},
        )
