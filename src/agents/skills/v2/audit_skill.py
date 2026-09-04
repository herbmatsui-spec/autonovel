# src/agents/skills/v2/audit_skill.py
"""AuditSkill v2 - Enhanced version with specialist auditors preparation"""

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.audit import LogicalAuditor

import logging
logger = logging.getLogger(__name__)


class AuditSkillAgent(SkillAgent):
    """AuditAgent のスキルラッパー バージョン2 - 専門オーディター並列化準備版"""
    
    version = "2.0"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = LogicalAuditor(*args, **kwargs)
        self._v2_enhancements = {
            "specialist_auditors_parallel": True,
            "multi_layer_quality_assurance": True,
        }
    
    async def execute(self, ctx: AgentContext) -> AgentResult:
        await self._v2_pre_process(ctx)
        result = await self._agent.execute(ctx)
        await self._v2_post_process(ctx, result)
        return result
    
    async def _v2_pre_process(self, ctx: AgentContext):
        if ctx.artifacts.get("regeneration_focus"):
            ctx.artifacts["audit_v2_enhanced"] = True
            logger.info(f"AuditSkillAgent v2: 再生成モード - 専門オーディター並列化準備有効")
    
    async def _v2_post_process(self, ctx: AgentContext, result: AgentResult):
        if result.artifacts.get("audit_result"):
            logger.debug(f"AuditSkillAgent v2: 監査完了")