"""キャラクター立ち絵生成サービス。"""

import logging
import time

from src.models.illustration import IllustrationRequest, IllustrationResult, IllustrationType
from src.services.illustration.model_selector import resolve_request_model
from src.services.illustration.prompts import apply_safety_modifier, build_character_prompt
from src.services.image_service import ImageService

logger = logging.getLogger(__name__)


class CharacterIllustrator:
    """キャラクター設定から立ち絵を生成する。"""

    def __init__(self, image_service: ImageService):
        self.image_service = image_service

    async def generate(self, request: IllustrationRequest) -> IllustrationResult:
        """キャラクターデータから立ち絵を生成する。"""
        start = time.time()

        character_data = request.book_context or {}
        prompt = request.prompt_override or build_character_prompt(character_data)
        prompt = apply_safety_modifier(prompt, request.safety_level, IllustrationType.CHARACTER)

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
