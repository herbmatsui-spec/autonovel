import asyncio
import json
from typing import Any

import websockets

from .base import ImageGenerationRequest, ImageGenerationResult, ImageGeneratorClient


class ComfyUIClient(ImageGeneratorClient):
    def __init__(
        self,
        base_url: str = "http://localhost:8188",
        websocket_timeout: float = 120.0,
        max_retries: int = 3,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.websocket_timeout = websocket_timeout
        self.max_retries = max_retries

    async def generate_image(self, req: ImageGenerationRequest) -> ImageGenerationResult:
        prompt_data = {
            "prompt": req.prompt,
            "negative_prompt": req.negative_prompt,
            "width": req.width,
            "height": req.height,
            "steps": req.steps,
            "cfg_scale": req.cfg_scale,
            "seed": req.seed if req.seed >= 0 else -1,
        }
        if req.lora_tags:
            prompt_data["prompt"] = f"{req.prompt}, {' ,'.join(req.lora_tags)}"

        last_error = None
        for attempt in range(self.max_retries):
            try:
                async with asyncio.Timeout(self.websocket_timeout):
                    async with websockets.connect(
                        f"ws://{self.base_url.split('://')[1]}/ws"
                    ) as websocket:
                        job_id = await self._queue_prompt(websocket, prompt_data)
                        result = await self._wait_for_result(websocket, job_id)
                        image_bytes = self._extract_image_from_result(result)
                        metadata = self._extract_metadata(result, req)
                        return ImageGenerationResult(
                            image_bytes=image_bytes,
                            format="png",
                            seed_used=metadata.get("seed", req.seed),
                            metadata=metadata,
                        )
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        raise RuntimeError(f"ComfyUI generation failed after {self.max_retries} attempts") from last_error

    async def _queue_prompt(self, websocket: Any, prompt_data: dict[str, Any]) -> str:
        payload = {"prompt": prompt_data}
        await websocket.send(json.dumps(payload))
        response = await websocket.recv()
        result = json.loads(response)
        return result["flow_key"]

    async def _wait_for_result(self, websocket: Any, job_id: str) -> dict[str, Any]:
        while True:
            response = await websocket.recv()
            data = json.loads(response)
            if data.get("job_id") == job_id and data.get("status") == "completed":
                return data

    def _extract_image_from_result(self, result: dict[str, Any]) -> bytes:
        outputs = result.get("outputs", {})
        for output in outputs.values():
            if isinstance(output, dict) and "images" in output:
                image_data = output["images"][0]
                if "data" in image_data:
                    import base64

                    return base64.b64decode(image_data["data"])
                elif "url" in image_data:
                    import aiohttp

                    async def fetch():
                        async with aiohttp.ClientSession() as session:
                            async with session.get(image_data["url"]) as resp:
                                return await resp.read()

                    return asyncio.run(fetch())
        raise RuntimeError("No image found in ComfyUI result")

    def _extract_metadata(self, result: dict[str, Any], req: ImageGenerationRequest) -> dict:
        return {
            "provider": "comfyui",
            "prompt": req.prompt,
            "negative_prompt": req.negative_prompt,
            "width": req.width,
            "height": req.height,
            "steps": req.steps,
            "cfg_scale": req.cfg_scale,
            "seed": req.seed,
        }