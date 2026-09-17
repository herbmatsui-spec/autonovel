"""モック画像生成クライアント（Pillow未インストール時もゼロクラッシュで動作）。"""
from __future__ import annotations

from io import BytesIO

from .base import ImageGenerationRequest, ImageGenerationResult, ImageGeneratorClient

DUMMY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00"
    b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


class MockImageClient(ImageGeneratorClient):
    def __init__(self, background_color: str = "#f0f0f0") -> None:
        self.background_color = background_color

    async def generate_image(self, req: ImageGenerationRequest) -> ImageGenerationResult:
        try:
            from PIL import Image

            image = Image.new("RGB", (req.width, req.height), self.background_color)
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            img_bytes = buffer.getvalue()
        except Exception:
            img_bytes = DUMMY_PNG

        return ImageGenerationResult(
            image_bytes=img_bytes,
            format="png",
            seed_used=req.seed if req.seed >= 0 else 42,
            metadata={"provider": "mock", "width": req.width, "height": req.height},
        )
