from io import BytesIO
from PIL import Image

from .base import ImageGenerationRequest, ImageGenerationResult, ImageGeneratorClient


class MockImageClient(ImageGeneratorClient):
    def __init__(self, background_color: str = "#f0f0f0") -> None:
        self.background_color = background_color

    async def generate_image(self, req: ImageGenerationRequest) -> ImageGenerationResult:
        image = Image.new("RGB", (req.width, req.height), self.background_color)
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        return ImageGenerationResult(
            image_bytes=buffer.getvalue(),
            format="png",
            seed_used=req.seed if req.seed >= 0 else 42,
            metadata={"provider": "mock", "width": req.width, "height": req.height},
        )