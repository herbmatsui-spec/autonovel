# src/agents/skills/v2/marketing_copy_skill.py
"""MarketingCopySkill v2 - Enhanced version with multi-language marketing and SEO support"""

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.skills.v1.marketing_copy import MarketingCopySkill

import logging
logger = logging.getLogger(__name__)


class MarketingCopySkillAgent(SkillAgent):
    """MarketingCopySkill のスキルラッパー バージョン2 - 多言語マーケティング・SEO対応版"""
    
    version = "2.0"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = MarketingCopySkill(*args, **kwargs)
        self._v2_enhancements = {
            "multi_language_marketing": True,
            "seo_optimization": True,
            "platform_specific_copy": True,
        }
    
    async def execute(self, ctx: AgentContext) -> AgentResult:
        await self._v2_pre_process(ctx)
        result = await self._agent.execute(ctx)
        await self._v2_post_process(ctx, result)
        return result
    
    async def _v2_pre_process(self, ctx: AgentContext):
        if ctx.artifacts.get("regeneration_focus"):
            ctx.artifacts["marketing_copy_v2_enhanced"] = True
            logger.info(f"MarketingCopySkillAgent v2: 再生成モード - 多言語マーケティング・SEO対応有効")
    
    async def _v2_post_process(self, ctx: AgentContext, result: AgentResult):
        if result.artifacts.get("marketing_copy"):
            logger.debug(f"MarketingCopySkillAgent v2: マーケティングコピー生成完了")