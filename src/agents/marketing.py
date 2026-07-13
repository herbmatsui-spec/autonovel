# agents/marketing.py
import logging
from typing import Any, Dict, Optional

from src.agents.base import BaseAgent
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class MarketingAgent(BaseAgent):
    """マーケティング素材（表紙案、キャッチコピー、あらすじ）を生成するエージェント。"""
    def __init__(self, repo: Any = None, llm: Optional[LLMService] = None, prompt_manager: Any = None):
        super().__init__(repo=repo, llm=llm)
        self.prompt_manager = prompt_manager

    async def generate_pack(self, book_title: str, synopsis: str, latest_ep: int, **kwargs) -> Dict[str, Any]:
        if self.prompt_manager is None:
            raise ValueError("PromptManager is required for MarketingAgent")
        prompt = self.prompt_manager.build_marketing_pack_prompt(
            book_title=book_title, synopsis=synopsis, latest_ep=latest_ep, **kwargs
        )
        result = await self.llm.generate_json(purpose="marketing", prompt=prompt)
        return result.get("metadata", {})

    async def run(self, *args, **kwargs):
        logger.info("MarketingAgent run invoked")
        return await self.generate_pack(**kwargs)

