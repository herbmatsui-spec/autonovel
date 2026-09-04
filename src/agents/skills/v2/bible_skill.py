# src/agents/skills/v2/bible_skill.py
"""BibleSkill v2 - Enhanced version with social media relationship modeling preparation"""

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.bible import BibleAgent

import logging
logger = logging.getLogger(__name__)


class BibleSkillAgent(SkillAgent):
    """BibleAgent のスキルラッパー バージョン2 - ソーシャルメディア風関係モデリング準備版"""
    
    version = "2.0"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = BibleAgent(*args, **kwargs)
        self._v2_enhancements = {
            "social_relationship_modeling": True,
            "dynamic_character_relations": True,
        }
    
    async def execute(self, ctx: AgentContext) -> AgentResult:
        await self._v2_pre_process(ctx)
        result = await self._agent.execute(ctx)
        await self._v2_post_process(ctx, result)
        return result
    
    async def _v2_pre_process(self, ctx: AgentContext):
        if ctx.artifacts.get("regeneration_focus"):
            ctx.artifacts["bible_v2_enhanced"] = True
            logger.info(f"BibleSkillAgent v2: 再生成モード - 関係性モデリング強化有効")
    
    async def _v2_post_process(self, ctx: AgentContext, result: AgentResult):
        if result.artifacts.get("bible"):
            logger.debug(f"BibleSkillAgent v2: Bible生成完了")