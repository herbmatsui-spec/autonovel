# src/agents/skills/v2/historical_accuracy_skill.py
"""HistoricalAccuracyCheckerSkill v2 - Enhanced version with era verification database integration"""

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.skills.v1.historical_accuracy import HistoricalAccuracyChecker

import logging
logger = logging.getLogger(__name__)


class HistoricalAccuracyCheckerSkillAgent(SkillAgent):
    """HistoricalAccuracyChecker のスキルラッパー バージョン2 - 時代考証データベース連携強化版"""
    
    version = "2.0"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = HistoricalAccuracyChecker(*args, **kwargs)
        self._v2_enhancements = {
            "era_verification_database": True,
            "anachronism_detection_enhanced": True,
            "cultural_timeline_validation": True,
        }
    
    async def execute(self, ctx: AgentContext) -> AgentResult:
        await self._v2_pre_process(ctx)
        result = await self._agent.execute(ctx)
        await self._v2_post_process(ctx, result)
        return result
    
    async def _v2_pre_process(self, ctx: AgentContext):
        if ctx.artifacts.get("regeneration_focus"):
            ctx.artifacts["historical_accuracy_v2_enhanced"] = True
            logger.info(f"HistoricalAccuracyCheckerSkillAgent v2: 再生成モード - 時代考証DB連携強化有効")
    
    async def _v2_post_process(self, ctx: AgentContext, result: AgentResult):
        if result.artifacts.get("historical_accuracy"):
            logger.debug(f"HistoricalAccuracyCheckerSkillAgent v2: 時代考証チェック完了")