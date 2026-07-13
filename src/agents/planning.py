# agents/planning.py
import logging
from typing import Any, Dict, Optional

from src.agents.base import BaseAgent
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)

class PlanningAgent(BaseAgent):
    """企画・プロット立案を担当するエージェント。
    LLM にアーク生成プロンプトを投げ、JSON 形式でアーク案を受け取る。
    """
    def __init__(self, repo: Any = None, llm: Optional[LLMService] = None, prompt_manager: Any = None):
        super().__init__(repo=repo, llm=llm)
        self.prompt_manager = prompt_manager

    async def generate_arcs(self, title: str, synopsis: str, target_eps: int, **kwargs) -> Dict[str, Any]:
        prompt = self.prompt_manager.build_arc_generation_prompt(
            title=title, synopsis=synopsis, target_eps=target_eps, **kwargs
        )
        result = await self.llm.generate_json(
            purpose="planning",
            prompt=prompt,
            response_schema=None,  # 必要に応じて Pydantic スキーマを指定
        )
        if result.get("success"):
            return result["metadata"]
        raise RuntimeError("Arc generation failed")

    async def run(self, *args, **kwargs):
        logger.info("PlanningAgent run invoked")
        return await self.generate_arcs(**kwargs)

