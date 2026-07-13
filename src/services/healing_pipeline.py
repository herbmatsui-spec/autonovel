import logging
from typing import Any

logger = logging.getLogger(__name__)

class HealingPipeline:
    """不整合修復パイプライン"""
    def __init__(self, llm: Any, prompt_manager: Any):
        self.llm = llm
        self.prompt_manager = prompt_manager

    async def repair(self, content: str, conflict_report: str) -> str:
        if self.prompt_manager is None:
            return content
        prompt = self.prompt_manager.build_global_repair_prompt(
            conflict_report=conflict_report,
            synopsis=content,
            world_rules="",
            mc_profile="",
        )
        result = await self.llm.generate_text(purpose="audit", prompt=prompt)
        return result or content
