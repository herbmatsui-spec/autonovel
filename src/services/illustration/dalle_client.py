import asyncio

import httpx

from .base import ImageGenerationRequest, ImageGenerationResult, ImageGeneratorClient


class DALLEResult(ImageGenerationResult):
    pass


class DalleClient(ImageGeneratorClient):
    def __init__(
        self,
        base_url: str = "https://api.openai.com",
        api_key: str = "",
        timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries

    async def generate_image(self, req: ImageGenerationRequest) -> ImageGenerationResult:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "dall-e-3",
            "prompt": req.prompt,
            "size": f"{req.width}x{req.height}",
            "quality": "standard",
            "n": 1,
        }

        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/v1/images/generations",
                        json=payload,
                        headers=headers,
                    )
                    response.raise_for_status()
                    data = response.json()
                    image_url = data["data"][0]["url"]
                    async with httpx.AsyncClient(timeout=self.timeout) as dl_client:
                        dl_response = await dl_client.get(image_url)
                        dl_response.raise_for_status()
                        image_bytes = dl_response.content
                    return ImageGenerationResult(
                        image_bytes=image_bytes,
                        format="png",
                        seed_used=req.seed,
                        metadata={"provider": "dalle3", "url": image_url},
                    )
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        raise RuntimeError(f"DALL-E 3 generation failed after {self.max_retries} attempts") from last_error
