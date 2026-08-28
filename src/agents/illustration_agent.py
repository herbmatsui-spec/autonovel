import logging
import time
from typing import Any, Dict, List, Optional

from src.agents.base import BaseAgent
from src.models.illustration import (
    IllustrationRequest,
    IllustrationResult,
    IllustrationType,
)
from src.services.illustration import (
    CharacterIllustrator,
    CoverGenerator,
    SceneIllustrationService,
    SceneIllustrator,
)
from src.services.illustration.model_selector import _type_value, is_r15, resolve_request_model
from src.services.image_service import ImageService

logger = logging.getLogger(__name__)


class IllustrationAgent(BaseAgent):
    """イラスト作成サブエージェント（表紙 / 挿絵 / キャラクター）。

    request は src / autonovel.src いずれの経路で生成された IllustrationRequest
    でも受け付けられるよう、isinstance に依存せず属性で判定する。
    """

    AGENT_NAME = "illustration"
    DISPLAY_NAME = "イラスト作成サブエージェント"

    def __init__(self, image_service: ImageService, bible_service: Optional[Any] = None, **kwargs):
        super().__init__(**kwargs)
        self.image_service = image_service
        self.bible_service = bible_service
        self.cover_generator = CoverGenerator(image_service)
        self.character_illustrator = CharacterIllustrator(image_service, bible_service=bible_service)
        self.scene_illustrator = SceneIllustrator(image_service)
        self.scene_service = SceneIllustrationService(image_service, llm=self.llm)

    def _coerce_request(self, request):
        """dict なら IllustrationRequest に、オブジェクトならそのまま返す。"""
        if isinstance(request, dict):
            return IllustrationRequest(**request)
        if hasattr(request, "illustration_type") and hasattr(request, "book_id"):
            return request
        raise ValueError("Invalid or missing illustration request")

    async def run(self, **kwargs) -> Dict[str, Any]:
        """エージェントのメイン実行ロジック。

        kwargs:
            - request: IllustrationRequest
        """
        try:
            request = self._coerce_request(kwargs.get("request"))
            kind = _type_value(request.illustration_type)
            if kind == IllustrationType.COVER.value:
                result = await self._generate_cover(request)
            elif kind == IllustrationType.CHARACTER.value:
                result = await self._generate_character(request)
            else:
                result = await self._generate_episode(request)

            illustration_id = await self._persist(request, result)
            result.illustration_id = illustration_id
            return {"status": "success", "result": result}
        except Exception as e:  # noqa: BLE001
            logger.error(f"IllustrationAgent error: {str(e)}")
            return {"status": "error", "message": str(e)}

    async def _generate_cover(self, request: IllustrationRequest) -> IllustrationResult:
        return await self.cover_generator.generate(request)

    async def _generate_character(self, request: IllustrationRequest) -> IllustrationResult:
        return await self.character_illustrator.generate(request)

    async def _generate_episode(self, request: IllustrationRequest) -> IllustrationResult:
        """話数ごとの挿絵（単一）。scene_text があればそのシーンを描画。"""
        if getattr(request, "scene_text", None):
            return await self.scene_illustrator.generate_for_scene(request.scene_text, request)

        # scene_text がない場合は book_context から汎用エピソードプロンプトを構築
        ctx = request.book_context or {}
        title = ctx.get("title", "")
        genre = ctx.get("genre", "")
        concept = ctx.get("concept", "")
        parts = [
            f"Scene illustration for episode {getattr(request, 'episode_number', None)}.",
        ]
        if title:
            parts.append(f"Title: {title}.")
        if genre:
            parts.append(f"Genre: {genre}.")
        if concept:
            parts.append(f"Atmosphere: {concept}.")
        parts.append(
            "Detailed background, cinematic lighting, rich detail, no text or letters in image."
        )
        prompt = " ".join(parts)
        if is_r15(request.safety_level):
            prompt += " Tasteful R15 artistic representation, intimate but not explicit."

        start = time.time()
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

    async def generate_episode_scenes(
        self, request: IllustrationRequest
    ) -> List[IllustrationResult]:
        """本文から複数シーンを抽出し、各シーンの挿絵を生成して返す（シーン抽出機能）。"""
        results = await self.scene_service.generate(request)
        for r in results:
            r.illustration_id = await self._persist(request, r)
        return results

    async def _persist(self, request, result: IllustrationResult) -> Optional[int]:
        """生成結果をDBに保存する（repo がなければスキップ）。"""
        if self.repo is None or not hasattr(self.repo, "create_illustration"):
            return None
        try:
            return await self.repo.create_illustration(
                book_id=request.book_id,
                illustration_type=_type_value(request.illustration_type),
                image_url=result.image_url,
                prompt=result.prompt,
                episode_number=getattr(request, "episode_number", None),
                character_id=getattr(request, "character_id", None),
                model=result.model_used,
                safety_level=_type_value(request.safety_level),
                generation_time_ms=result.generation_time_ms,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to persist illustration: {e}")
            return None
