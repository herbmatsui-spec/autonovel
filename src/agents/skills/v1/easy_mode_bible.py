# src/agents/skills/v1/easy_mode_bible.py
"""easy_mode 専用 BibleSkill - 簡易バイブル生成"""
from __future__ import annotations

import logging
from typing import Any

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName

logger = logging.getLogger(__name__)


class EasyModeBibleSkill(SkillAgent):
    """かんたんモード用バイブル生成スキル"""

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

    async def execute(self, ctx: AgentContext) -> AgentResult:
        """簡易バイブル生成を実行"""
        try:
            book_id = ctx.artifacts.get("book_id")
            genre = ctx.artifacts.get("genre", "fantasy")
            keywords = ctx.artifacts.get("keywords", "")
            title = ctx.artifacts.get("title", "無題")

            if not book_id:
                return AgentResult(
                    next_agent=None,
                    artifacts={},
                    error="book_id is required for bible generation",
                )

            # 既存の BibleAgent / WorldBibleGenerator ロジックを簡易化して実行
            from src.services.bible_service import WorldBibleGenerator
            bible_generator = WorldBibleGenerator(
                repo=self.repo,
                llm=self.llm,
                pm=self.pm,
                debate=None,
                marketing=None,
                auditor=None,
            )

            _, bible = await bible_generator.create_hegemony_plan(
                genre=genre,
                keywords=keywords,
                title=title,
                reporter=ctx.artifacts.get("reporter"),
            )

            return AgentResult(
                next_agent=AgentName.CONTEXT_BUILDER,
                artifacts={
                    "bible": bible,
                },
            )
        except Exception as e:
            logger.exception("EasyModeBibleSkill failed")
            return AgentResult(
                next_agent=None,
                artifacts={},
                error=f"Bible generation failed: {e}",
            )