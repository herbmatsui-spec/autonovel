"""開発・テスト用ゼロコストモック画像生成アダプタ (v5.0 Step 4).

CI/CDパイプラインおよびローカル開発環境で、APIコスト0円・遅延0msで
画像生成フロー全体（表紙、挿絵）を検証可能にする。
"""
from __future__ import annotations

from src.services.illustration.adapters.base import (
    GeneratedImageResult,
    ImageGenerationAdapter,
    ImagePromptRequest,
)

# 1x1 透明PNGダミーバイト列
DUMMY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00"
    b"\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


class MockImageAdapter(ImageGenerationAdapter):
    """開発・CIテスト用ダミー画像生成アダプタ（コスト0円・即時応答）。"""

    @property
    def provider_name(self) -> str:
        return "mock"

    async def generate_image(self, request: ImagePromptRequest) -> GeneratedImageResult:
        return GeneratedImageResult(
            image_bytes=DUMMY_PNG,
            format="png",
            provider="mock",
            cost_usd=0.0,
            metadata={
                "mock_prompt": request.prompt,
                "aspect_ratio": request.aspect_ratio,
                "style": request.style,
            },
        )
