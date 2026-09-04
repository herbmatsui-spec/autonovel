# src/agents/skills/audit_skill.py
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.audit_agent import AuditAgent


class AuditSkill(SkillAgent):
    """AuditAgent のスキルラッパー"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = AuditAgent(*args, **kwargs)

    async def execute(self, ctx: AgentContext) -> AgentResult:
        return await self._agent.execute(ctx)