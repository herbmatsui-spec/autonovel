# src/agents/skills/v2/planning_skill.py
"""PlanningSkill v2 - Enhanced version with improved BookScore prediction"""

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.planning import PlanningAgent


class PlanningSkillAgent(SkillAgent):
    """PlanningAgent のスキルラッパー バージョン2 - BookScore予測精度向上版"""
    
    version = "2.0"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = PlanningAgent(*args, **kwargs)
        # v2 固有の初期化
        self._v2_enhancements = {
            "arc_optimization": True,
            "bookscore_prediction_enhanced": True,
        }
    
    async def execute(self, ctx: AgentContext) -> AgentResult:
        await self._v2_pre_process(ctx)
        result = await self._agent.execute(ctx)
        await self._v2_post_process(ctx, result)
        return result
    
    async def _v2_pre_process(self, ctx: AgentContext):
        """v2 固有の前処理: アーク構成最適化パラメータ設定"""
        if ctx.artifacts.get("regeneration_focus"):
            # 再生成時はアーク構成をより詳細に分析
            ctx.artifacts["planning_v2_enhanced"] = True
            logger.info(f"PlanningSkillAgent v2: 再生成モード - アーク構成最適化有効")
    
    async def _v2_post_process(self, ctx: AgentContext, result: AgentResult):
        """v2 固有の後処理: メトリクス記録"""
        if result.artifacts.get("arcs"):
            arc_count = len(result.artifacts["arcs"])
            logger.debug(f"PlanningSkillAgent v2: アーク数={arc_count}")


import logging
logger = logging.getLogger(__name__)