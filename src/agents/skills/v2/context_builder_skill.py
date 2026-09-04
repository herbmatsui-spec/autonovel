# src/agents/skills/v2/context_builder_skill.py
"""ContextBuilderSkill v2 - Enhanced version with 4-layer compression preparation"""

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.context_builder_agent import ContextBuilderAgent

import logging
logger = logging.getLogger(__name__)


class ContextBuilderSkillAgent(SkillAgent):
    """ContextBuilderAgent のスキルラッパー バージョン2 - 4階層圧縮対応準備版"""
    
    version = "2.0"
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = ContextBuilderAgent(*args, **kwargs)
        self._v2_enhancements = {
            "four_layer_compression": True,
            "rag_precision_enhanced": True,
        }
    
    async def execute(self, ctx: AgentContext) -> AgentResult:
        await self._v2_pre_process(ctx)
        result = await self._agent.execute(ctx)
        await self._v2_post_process(ctx, result)
        return result
    
    async def _v2_pre_process(self, ctx: AgentContext):
        if ctx.artifacts.get("regeneration_focus"):
            ctx.artifacts["context_builder_v2_enhanced"] = True
            logger.info(f"ContextBuilderSkillAgent v2: 再生成モード - 圧縮・RAG精度強化有効")
    
    async def _v2_post_process(self, ctx: AgentContext, result: AgentResult):
        if result.artifacts.get("writing_context"):
            logger.debug(f"ContextBuilderSkillAgent v2: コンテキスト構築完了")