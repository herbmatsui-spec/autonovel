import base64
import time

import httpx

from .base import ImageGenerationRequest, ImageGenerationResult, ImageGeneratorClient


class SDWebUIClient(ImageGeneratorClient):
    def __init__(
        self,
        base_url: str = "http://localhost:7860",
        timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries

    async def generate_image(self, req: ImageGenerationRequest) -> ImageGenerationResult:
        payload = {
            "prompt": req.prompt,
            "negative_prompt": req.negative_prompt,
            "width": req.width,
            "height": req.height,
            "steps": req.steps,
            "cfg_scale": req.cfg_scale,
            "seed": req.seed if req.seed >= 0 else None,
        }
        if req.lora_tags:
            lora_prompt = ", ".join(req.lora_tags)
            payload["prompt"] = f"{req.prompt}, {lora_prompt}"

        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/sdapi/v1/txt2img",
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    if not data.get("images"):
                        raise RuntimeError("SD WebUI returned no images")
                    image_data = data["images"][0]
                    image_bytes = base64.b64decode(image_data.split(",", 1)[0])
                    seed_used = data.get("info", {}).get("seed", req.seed)
                    if seed_used is None:
                        seed_used = req.seed
                    metadata = {
                        "provider": "sd_webui",
                        "prompt": req.prompt,
                        "negative_prompt": req.negative_prompt,
                        "width": req.width,
                        "height": req.height,
                        "steps": req.steps,
                        "cfg_scale": req.cfg_scale,
                        "seed": seed_used,
                    }
                    return ImageGenerationResult(
                        image_bytes=image_bytes,
                        format="png",
                        seed_used=seed_used,
                        metadata=metadata,
                    )
            except (httpx.HTTPError, ValueError, KeyError) as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    await time.sleep(2 ** attempt)
        raise RuntimeError(f"SD WebUI generation failed after {self.max_retries} attempts") from last_error