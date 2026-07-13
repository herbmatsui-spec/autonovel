# agents/bible.py
import logging
from typing import Any, Dict, Optional

from src.agents.base import BaseAgent
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class BibleAgent(BaseAgent):
    """世界観設定・キャラクター設定の生成を担当するエージェント。
    LLM とプロンプトマネージャを利用して設定情報を生成する。
    """
    def __init__(self, repo: Any = None, llm: Optional[LLMService] = None, prompt_manager: Any = None):
        super().__init__(repo=repo, llm=llm)
        self.prompt_manager = prompt_manager

    async def generate_bible(self, title: str, synopsis: str, target_eps: int, concept: str = "", **kwargs) -> Dict[str, Any]:
        if self.prompt_manager is None:
            raise ValueError("PromptManager is required for BibleAgent")
        world_prompt = self.prompt_manager.build_world_creation_prompt(
            genre=kwargs.get("genre", "fantasy"),
            keywords=kwargs.get("keywords", ""),
            response_schema=None,
            concept=concept,
            target_eps=target_eps,
        )
        world_result = await self.llm.generate_json(purpose="planning", prompt=world_prompt)
        world_data = world_result.get("metadata", {})
        return world_data

    async def run(self, *args, **kwargs):
        logger.info("BibleAgent run invoked")
        return await self.generate_bible(**kwargs)

