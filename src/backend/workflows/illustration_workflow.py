import logging
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from src.shared.utils import StatusReporter
from src.backend.workflows.base_workflow import BaseWorkflow
from src.agents.illustration_agent import IllustrationAgent
from src.models.illustration import (
    IllustrationRequest,
    IllustrationResult,
    IllustrationType,
    IllustrationModel,
    SafetyLevel,
)

logger = logging.getLogger(__name__)

class IllustrationWorkflow(BaseWorkflow):
    """挿絵制作ワークフロー: 単一またはバッチでの画像生成を管理"""

    def __init__(
        self,
        illustration_agent: IllustrationAgent,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.illustration_agent = illustration_agent

    async def execute(self, reporter: StatusReporter, **kwargs) -> Dict[str, Any]:
        """
        挿絵生成ワークフローの実行
        kwargs:
            - book_id: int
            - settings: Dict (EasyModeStoreからの設定)
        """
        book_id = kwargs.get("book_id")
        settings = kwargs.get("settings", {})
        
        if not book_id:
            raise ValueError("book_id is required for IllustrationWorkflow")

        enabled = settings.get("enableIllustration", False)
        if not enabled:
            logger.info(f"Illustration generation is disabled for book {book_id}")
            return {"status": "skipped", "message": "Illustrations disabled"}

        results = []
        
        # 1. 表紙の生成
        if settings.get("generateCover", True):
            reporter.update_progress(0, 1, "表紙イラストを生成中...")
            cover_request = IllustrationRequest(
                book_id=book_id,
                illustration_type=IllustrationType.COVER,
                model=IllustrationModel[settings.get("illustrationModel", "QUALITY").upper()],
                safety_level=self._determine_safety_level(settings)
            )
            res = await self.illustration_agent.run(request=cover_request)
            if res["status"] == "success":
                results.append(res["result"])
            else:
                logger.error(f"Cover generation failed: {res.get('message')}")

        # 2. 話数ごとの挿絵生成 (バッチ処理)
        if settings.get("generateEpisodeIllustrations", False):
            interval = settings.get("episodeInterval", 3)
            
            # 本の全エピソード数を取得 (repo経由)
            chapters = await self.repo.get_chapters(book_id)
            total_chapters = len(chapters)
            
            if total_chapters > 0:
                target_chapters = range(1, total_chapters + 1, interval)
                total_steps = len(target_chapters)
                
                for i, ep_num in enumerate(target_chapters):
                    reporter.update_progress(
                        (i + 1) / total_steps, 
                        1, 
                        f"第{ep_num}話の挿絵を生成中..."
                    )
                    
                    ep_request = IllustrationRequest(
                        book_id=book_id,
                        illustration_type=IllustrationType.EPISODE,
                        episode_number=ep_num,
                        model=IllustrationModel[settings.get("illustrationModel", "QUALITY").upper()],
                        safety_level=self._determine_safety_level(settings)
                    )
                    res = await self.illustration_agent.run(request=ep_request)
                    if res["status"] == "success":
                        results.append(res["result"])
                    else:
                        logger.error(f"Episode {ep_num} generation failed: {res.get('message')}")

        return {
            "status": "success",
            "illustrations": results
        }

    def _determine_safety_level(self, settings: Dict[str, Any]) -> SafetyLevel:
        """設定に基づいてセーフティレベルを決定"""
        if settings.get("enableErotic", False):
            return SafetyLevel.R15_CONTENT
        return SafetyLevel.BLOCK_SOME
