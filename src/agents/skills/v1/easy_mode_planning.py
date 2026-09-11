# src/agents/skills/v1/easy_mode_planning.py
"""easy_mode 専用 PlanningSkill - 簡易企画生成"""
from __future__ import annotations

import logging
from typing import Any

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName

logger = logging.getLogger(__name__)


class EasyModePlanningSkill(SkillAgent):
    """かんたんモード用企画生成スキル"""

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
        """簡易企画生成を実行"""
        try:
            title = ctx.artifacts.get("title", "無題")
            synopsis = ctx.artifacts.get("synopsis", "")
            target_eps = ctx.artifacts.get("target_eps", 10)
            genre = ctx.artifacts.get("genre", "fantasy")
            keywords = ctx.artifacts.get("keywords", "")
            concept = ctx.artifacts.get("concept", "")

            # 既存の PlanningAgent ロジックを簡易化して実行
            from src.agents.planning import PlanningAgent
            planner = PlanningAgent(repo=self.repo, llm=self.llm, prompt_manager=self.pm)
            
            book_id, bible = await planner.create_hegemony_plan(
                genre=genre,
                keywords=keywords,
                style_key=None,
                concept=concept,
                title=title,
                cheat_scale=3,
                growth_curve="standard",
                system_assist="standard",
                cost_severity="standard",
                target_eps=target_eps,
                initial_plot_limit=3,
                enable_erotic=False,
                erotic_intensity=2,
                reporter=ctx.artifacts.get("reporter"),
            )

            return AgentResult(
                next_agent=AgentName.PLOT,
                artifacts={
                    "book_id": book_id,
                    "bible": bible,
                    "title": title,
                    "synopsis": synopsis,
                    "target_eps": target_eps,
                    "genre": genre,
                    "keywords": keywords,
                    "concept": concept,
                },
            )
        except Exception as e:
            logger.exception("EasyModePlanningSkill failed")
            return AgentResult(
                next_agent=None,
                artifacts={},
                error=f"Planning failed: {e}",
            )