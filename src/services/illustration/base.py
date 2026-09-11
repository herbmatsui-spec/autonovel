from abc import ABC, abstractmethod
from dataclasses import dataclass
import io
from PIL import Image
from typing import Dict, Any

@dataclass
class ImageGenerationRequest:
    prompt: str
    negative_prompt: str = ""
    width: int = 512
    height: int = 768
    steps: int = 25
    cfg_scale: float = 7.0
    seed: int = -1
    lora_tags: list[str] | None = None

@dataclass
class ImageGenerationResult:
    image_bytes: bytes
    format: str = "png"
    seed_used: int = -1
    metadata: dict = None

class ImageGeneratorClient(ABC):
    @abstractmethod
    async def generate_image(self, req: ImageGenerationRequest) -> ImageGenerationResult:
        pass


def extract_png_metadata(image_bytes: bytes) -> Dict[str, Any]:
    """
    PNG バイナリからメタデータを抽出するヘルパー関数。
    シード値、プロンプト、サイズなどをPNGのIDATから抽出可能だが、
    簡易的にダミーの情報を返す。
    """
    try:
        with Image.open(io.BytesIO(image_bytes)) as img:
            width, height = img.size
            format = img.format
    except Exception:
        width = height = 0
        format = None
    
    return {
        "width": width,
        "height": height,
        "format": format,
        "has_text": False,
        "has_watermark": False,
    }