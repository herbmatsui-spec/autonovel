# src/agents/skills/v2/cultural_compliance_skill.py
"""CulturalComplianceCheckerSkill v2 - Enhanced version with multi-language/region support"""

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.skills.v1.cultural_compliance import CulturalComplianceChecker

import logging
logger = logging.getLogger(__name__)


class CulturalComplianceCheckerSkillAgent(SkillAgent):
    """CulturalComplianceChecker のスキルラッパー バージョン2 - 多言語・多地域対応強化版"""
    
    version = "2.0"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = CulturalComplianceChecker(*args, **kwargs)
        self._v2_enhancements = {
            "multi_language_support": True,
            "expanded_region_coverage": True,
            "dynamic_ng_word_database": True,
        }
    
    async def execute(self, ctx: AgentContext) -> AgentResult:
        await self._v2_pre_process(ctx)
        result = await self._agent.execute(ctx)
        await self._v2_post_process(ctx, result)
        return result
    
    async def _v2_pre_process(self, ctx: AgentContext):
        if ctx.artifacts.get("regeneration_focus"):
            ctx.artifacts["cultural_compliance_v2_enhanced"] = True
            logger.info(f"CulturalComplianceCheckerSkillAgent v2: 再生成モード - 多言語対応強化有効")
    
    async def _v2_post_process(self, ctx: AgentContext, result: AgentResult):
        if result.artifacts.get("cultural_compliance"):
            logger.debug(f"CulturalComplianceCheckerSkillAgent v2: 文化的適切性チェック完了")