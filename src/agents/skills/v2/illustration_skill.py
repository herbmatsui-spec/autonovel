# src/agents/skills/v2/illustration_skill.py
"""IllustrationSkill v2 - Enhanced version with visual-textual synergy specialization"""

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.illustration_agent import IllustrationAgent

import logging
logger = logging.getLogger(__name__)


class IllustrationSkillAgent(SkillAgent):
    """IllustrationAgent のスキルラッパー バージョン2 - Visual-textual synergy 特化版"""
    
    version = "2.0"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = IllustrationAgent(*args, **kwargs)
        self._v2_enhancements = {
            "visual_textual_synergy_focus": True,
            "prompt_regeneration_enhanced": True,
            "emotion_tone_matching": True,
        }
    
    async def execute(self, ctx: AgentContext) -> AgentResult:
        await self._v2_pre_process(ctx)
        result = await self._agent.execute(ctx)
        await self._v2_post_process(ctx, result)
        return result
    
    async def _v2_pre_process(self, ctx: AgentContext):
        regeneration_focus = ctx.artifacts.get("regeneration_focus", [])
        if "visual_textual_synergy" in regeneration_focus:
            ctx.artifacts["illustration_v2_enhanced"] = True
            logger.info(f"IllustrationSkillAgent v2: 再生成モード - Visual-textual synergy 特化有効")
    
    async def _v2_post_process(self, ctx: AgentContext, result: AgentResult):
        if result.artifacts.get("illustration_result"):
            logger.debug(f"IllustrationSkillAgent v2: 挿絵生成完了")