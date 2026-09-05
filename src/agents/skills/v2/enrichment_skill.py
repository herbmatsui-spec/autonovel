# src/agents/skills/v2/enrichment_skill.py
"""EnrichmentSkill v2 - EnrichmentAgent のスキルラッパー（v2・将来のA/Bテスト用）"""
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.enrichment_agent import EnrichmentAgent


class EnrichmentSkill(SkillAgent):
    """EnrichmentAgent のスキルラッパー（v2）"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = EnrichmentAgent(*args, **kwargs)

    async def execute(self, ctx: AgentContext) -> AgentResult:
        return await self._agent.execute(ctx)