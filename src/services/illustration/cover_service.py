"""表紙生成サービス。"""

import logging
import time

from src.models.illustration import IllustrationRequest, IllustrationResult, IllustrationType
from src.services.illustration.model_selector import resolve_request_model
from src.services.illustration.prompts import apply_safety_modifier, build_cover_prompt
from src.services.image_service import ImageService

logger = logging.getLogger(__name__)


class CoverGenerator:
    """表紙イラストを生成するサービス。"""

    def __init__(self, image_service: ImageService):
        self.image_service = image_service

    async def generate(self, request: IllustrationRequest) -> IllustrationResult:
        """表紙用のプロンプトを構築して画像を生成する。"""
        start = time.time()

        prompt = request.prompt_override or build_cover_prompt(
            request.book_context, variation=request.episode_number or 0
        )
        prompt = apply_safety_modifier(prompt, request.safety_level, IllustrationType.COVER)

        image_url = await self.image_service.generate(
            prompt=prompt,
            model=resolve_request_model(request),
            aspect_ratio=request.aspect_ratio,
            safety_level=request.safety_level,
        )

        elapsed = int((time.time() - start) * 1000)
        return IllustrationResult(
            request=request,
            image_url=image_url,
            prompt=prompt,
            model_used=resolve_request_model(request),
            generation_time_ms=elapsed,
        )

    async def generate_variations(
        self, request: IllustrationRequest, count: int = 3
    ) -> list[IllustrationResult]:
        """バリエーション付きで複数の表紙を生成する。"""
        results: list[IllustrationResult] = []
        for i in range(count):
            variant = IllustrationRequest(
                book_id=request.book_id,
                illustration_type=IllustrationType.COVER,
                episode_number=i,
                book_context=request.book_context,
                model=request.model,
                safety_level=request.safety_level,
                aspect_ratio=request.aspect_ratio,
                prompt_override=request.prompt_override,
            )
            results.append(await self.generate(variant))
        return results
