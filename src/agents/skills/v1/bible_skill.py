# src/agents/skills/bible_skill.py
from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult
from src.agents.bible import BibleAgent


class BibleSkill(SkillAgent):
    """BibleAgent のスキルラッパー"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._agent = BibleAgent(*args, **kwargs)

    async def execute(self, ctx: AgentContext) -> AgentResult:
        return await self._agent.execute(ctx)