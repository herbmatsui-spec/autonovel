"""ImageGenerationAdapter 抽象基底インターフェース (v5.0 Step 1).

自前GPUホスティング（月数万円）を撤廃し、外部従量API（DALL-E 3, fal.ai, Replicate等）へ
透過的に切り替えるためのアダプタ抽象基底クラス。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ImagePromptRequest:
    """画像生成リクエストパラメータ。"""

    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    aspect_ratio: str = "1:1"  # "1:1", "16:9", "9:16", "horizontal", "vertical"
    steps: int = 25
    seed: Optional[int] = None
    style: str = "anime"


@dataclass
class GeneratedImageResult:
    """画像生成結果。"""

    image_bytes: bytes
    format: str = "png"
    provider: str = "unknown"
    cost_usd: float = 0.0
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)


class ImageGenerationAdapter(ABC):
    """外部従量課金画像生成API用のアダプタ基底クラス。"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """プロバイダー識別子 (例: "dalle3", "fal_ai", "mock")"""
        pass

    @abstractmethod
    async def generate_image(self, request: ImagePromptRequest) -> GeneratedImageResult:
        """画像を1枚生成しバイトデータと消費コストを返す。"""
        pass
