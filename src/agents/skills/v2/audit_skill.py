# src/agents/skills/v2/audit_skill.py
"""AuditSkill v2 - Multi-layer quality assurance with 8 specialist auditors."""
from __future__ import annotations

import logging
from typing import Any

from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.skill_base import SkillAgent
from src.agents.specialists.adapter import AuditAggregatorNode

logger = logging.getLogger(__name__)


class AuditSkillAgent(SkillAgent):
    """AuditAgent のスキルラッパー バージョン2 - 8専門オーディター並列集約版"""

    version = "2.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._node = AuditAggregatorNode(
            weights_path="config/audit_weights.yaml",
            event_bus=self.event_bus,
            repo=self.repo,
            llm=self.llm,
        )
        self._v2_enhancements = {
            "specialist_auditors_parallel": True,
            "multi_layer_quality_assurance": True,
        }

    async def execute(self, ctx: AgentContext) -> AgentResult:
        """8専門オーディターを並列実行して品質監査を集約する"""
        await self._v2_pre_process(ctx)
        result = await self._node(ctx)
        await self._v2_post_process(ctx, result)
        return result

    async def _v2_pre_process(self, ctx: AgentContext):
        ctx.artifacts["audit_v2_active"] = True
        if ctx.artifacts.get("regeneration_focus"):
            ctx.artifacts["audit_v2_enhanced"] = True
            logger.info("AuditSkillAgent v2: 再生成フォーカス監査モード有効")

    async def _v2_post_process(self, ctx: AgentContext, result: AgentResult):
        if "audit_score" in result.artifacts:
            score = result.artifacts["audit_score"]
            logger.info(f"AuditSkillAgent v2: 8専門オーディター集約監査完了 (総合スコア: {score})")