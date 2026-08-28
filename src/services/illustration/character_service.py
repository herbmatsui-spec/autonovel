"""キャラクター立ち絵生成サービス。"""

import logging
import time

from typing import Any, Optional

from src.models.illustration import IllustrationRequest, IllustrationResult, IllustrationType
from src.services.illustration.model_selector import resolve_request_model
from src.services.illustration.prompts import apply_safety_modifier, build_character_prompt
from src.services.image_service import ImageService

logger = logging.getLogger(__name__)


class CharacterIllustrator:
    """キャラクター設定から立ち絵を生成する。"""

    def __init__(self, image_service: ImageService, bible_service: Optional[Any] = None):
        self.image_service = image_service
        self.bible_service = bible_service

    async def generate(self, request: IllustrationRequest) -> IllustrationResult:
        """キャラクターデータから立ち絵を生成する。"""
        start = time.time()

        character_data = dict(request.book_context or {})

        # BibleServiceから外見設定を自動補完
        if self.bible_service and request.book_id:
            try:
                char_name = character_data.get("name") or request.character_id or "mc"
                ctx = await self.bible_service.get_context_by_book_id(request.book_id)
                if ctx:
                    char_ctx = ctx.get_character(str(char_name))
                    if char_ctx:
                        if not character_data.get("appearance") and char_ctx.appearance:
                            character_data["appearance"] = char_ctx.appearance
                        if not character_data.get("name") and char_ctx.name:
                            character_data["name"] = char_ctx.name
                        if not character_data.get("role") and char_ctx.role:
                            character_data["role"] = char_ctx.role
                        if not character_data.get("traits") and char_ctx.personality:
                            character_data["traits"] = char_ctx.personality
                        if char_ctx.visual_tags:
                            existing_app = character_data.get("appearance", "")
                            tag_str = ", ".join(char_ctx.visual_tags)
                            if tag_str not in existing_app:
                                character_data["appearance"] = f"{existing_app}, {tag_str}".strip(", ")
            except Exception as e:
                logger.warning(f"Failed to enrich character data from BibleService: {e}")

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
