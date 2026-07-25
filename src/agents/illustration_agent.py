import logging
from typing import Any, Dict, List, Optional
from src.agents.base import BaseAgent
from src.services.image_service import ImageService
from src.models.illustration import (
    IllustrationRequest,
    IllustrationResult,
    IllustrationType,
    IllustrationModel,
    SafetyLevel,
)

logger = logging.getLogger(__name__)

class IllustrationAgent(BaseAgent):
    """挿絵制作サブエージェント"""

    def __init__(self, image_service: ImageService, **kwargs):
        super().__init__(**kwargs)
        self.image_service = image_service

    async def run(self, **kwargs) -> Dict[str, Any]:
        """
        エージェントのメイン実行ロジック
        kwargs: 
            - book_id: int
            - request: IllustrationRequest
        """
        request = kwargs.get("request")
        if not request or not isinstance(request, IllustrationRequest):
            # 辞書形式で渡された場合の変換
            if isinstance(request, dict):
                request = IllustrationRequest(**request)
            else:
                raise ValueError("Invalid or missing illustration request")

        try:
            if request.illustration_type == IllustrationType.COVER:
                result = await self._generate_cover(request)
            else:
                result = await self._generate_episode_illustration(request)
            
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            logger.error(f"IllustrationAgent error: {str(e)}")
            return {
                "status": "error",
                "message": str(e)
            }

    async def _generate_cover(self, request: IllustrationRequest) -> IllustrationResult:
        """表紙イラストの生成"""
        # 本来はここでLLMを使用して企画書等から詳細なプロンプトを生成する
        # 現時点ではプレースホルダーとして基本プロンプトを使用
        prompt = f"Professional book cover for book ID {request.book_id}. High quality, cinematic lighting."
        
        if request.safety_level == SafetyLevel.R15_CONTENT:
            prompt += " Tasteful R15 artistic representation, romantic atmosphere."

        image_url = await self.image_service.generate(
            prompt=prompt,
            model=request.model.value,
            safety_level=request.safety_level
        )

        return IllustrationResult(
            request=request,
            image_url=image_url,
            prompt=prompt,
            model_used=request.model.value,
            generation_time_ms=0 # 実際には計測して入れる
        )

    async def _generate_episode_illustration(self, request: IllustrationRequest) -> IllustrationResult:
        """話数ごとの挿絵生成"""
        # 本来はここでエピソード内容からプロンプトを生成する
        prompt = f"Scene illustration for episode {request.episode_number} of book {request.book_id}. Detailed background, cinematic."
        
        if request.safety_level == SafetyLevel.R15_CONTENT:
            prompt += " Tasteful R15 artistic representation, intimate but not explicit."

        image_url = await self.image_service.generate(
            prompt=prompt,
            model=request.model.value,
            safety_level=request.safety_level
        )

        return IllustrationResult(
            request=request,
            image_url=image_url,
            prompt=prompt,
            model_used=request.model.value,
            generation_time_ms=0
        )
