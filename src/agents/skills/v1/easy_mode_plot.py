# src/agents/skills/v1/easy_mode_plot.py
"""easy_mode 専用 PlotSkill - 簡易プロット生成"""
from __future__ import annotations

import logging
from typing import Any

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName

logger = logging.getLogger(__name__)


class EasyModePlotSkill(SkillAgent):
    """かんたんモード用プロット生成スキル"""

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
        """簡易プロット生成を実行"""
        try:
            book_id = ctx.artifacts.get("book_id")
            target_eps = ctx.artifacts.get("target_eps", 10)
            genre = ctx.artifacts.get("genre", "fantasy")
            bible = ctx.artifacts.get("bible")

            if not book_id:
                return AgentResult(
                    next_agent=None,
                    artifacts={},
                    error="book_id is required for plot generation",
                )

            # 既存の PlotAgent ロジックを簡易化して実行
            from src.agents.plot import PlotAgent
            plot_agent = PlotAgent(repo=self.repo, pm=self.pm, generate_json=self.llm.generate_json if self.llm else None)

            arcs = getattr(bible, "arcs", []) if bible else []
            
            results = await plot_agent.expand_plots(
                book_id=book_id,
                target_ep_list=list(range(1, target_eps + 1)),
                arcs=arcs,
                reporter=ctx.artifacts.get("reporter"),
                force=False,
                branch_id=ctx.branch_id,
            )

            return AgentResult(
                next_agent=AgentName.BIBLE,
                artifacts={
                    "plots": results,
                },
            )
        except Exception as e:
            logger.exception("EasyModePlotSkill failed")
            return AgentResult(
                next_agent=None,
                artifacts={},
                error=f"Plot generation failed: {e}",
            )