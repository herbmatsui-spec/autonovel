# src/agents/skills/v1/easy_mode_writing.py
"""easy_mode 専用 WritingSkill - 簡易本文生成"""
from __future__ import annotations

import logging
from typing import Any

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName

logger = logging.getLogger(__name__)


class EasyModeWritingSkill(SkillAgent):
    """かんたんモード用本文生成スキル"""

    def __init__(
        self,
        repo: Any = None,
        llm: Any = None,
        style_rag: Any = None,
        rag_prefetch: Any = None,
        pm: Any = None,
    ):
        super().__init__(repo=repo, llm=llm, style_rag=style_rag, rag_prefetch=rag_prefetch)
        self.pm = pm
        self._writing_agent = None

    @property
    def writing_agent(self):
        if self._writing_agent is None:
            from src.agents.writing.agent import WritingAgent
            self._writing_agent = WritingAgent(
                repo=self.repo,
                llm=self.llm,
                style_rag=self.style_rag,
                rag_prefetch=self.rag_prefetch,
                pm=self.pm,
            )
        return self._writing_agent

    async def execute(self, ctx: AgentContext) -> AgentResult:
        """簡易本文生成を実行"""
        try:
            writing_context = ctx.artifacts.get("writing_context")
            if not writing_context:
                return AgentResult(
                    next_agent=None,
                    artifacts={},
                    error="writing_context is required in artifacts",
                )

            book_id = ctx.book_id
            ep_num = ctx.ep_num

            text = await self.writing_agent.write_episode(
                book_id=book_id,
                ep_num=ep_num,
                context=writing_context,
            )

            return AgentResult(
                next_agent=AgentName.ILLUSTRATION,
                artifacts={
                    "drafted_text": text,
                },
            )
        except Exception as e:
            logger.exception("EasyModeWritingSkill failed")
            return AgentResult(
                next_agent=None,
                artifacts={},
                error=f"Writing failed: {e}",
            )