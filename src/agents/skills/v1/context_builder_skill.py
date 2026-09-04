# src/agents/skills/context_builder_skill.py
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.context_builder_agent import ContextBuilderAgent


class ContextBuilderSkill(SkillAgent):
    """ContextBuilderAgent のスキルラッパー"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = ContextBuilderAgent(*args, **kwargs)

    async def execute(self, ctx: AgentContext) -> AgentResult:
        return await self._agent.execute(ctx)