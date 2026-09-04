# src/agents/skills/illustration_skill.py
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.illustration_agent import IllustrationAgent


class IllustrationSkill(SkillAgent):
    """IllustrationAgent のスキルラッパー"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = IllustrationAgent(*args, **kwargs)

    async def execute(self, ctx: AgentContext) -> AgentResult:
        return await self._agent.execute(ctx)