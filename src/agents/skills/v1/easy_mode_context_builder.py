# src/agents/skills/v1/easy_mode_context_builder.py
"""easy_mode 専用 ContextBuilderSkill - 簡易コンテキスト構築"""
from __future__ import annotations

import logging
from typing import Any

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName

logger = logging.getLogger(__name__)


class EasyModeContextBuilderSkill(SkillAgent):
    """かんたんモード用コンテキスト構築スキル"""

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
        """簡易コンテキスト構築を実行"""
        try:
            book_id = ctx.book_id
            branch_id = ctx.branch_id
            ep_num = ctx.ep_num
            target_word_count = ctx.artifacts.get("target_word_count", 3000)
            style_tag = ctx.artifacts.get("style_tag")

            # ContextBuilderAgent を使用
            from src.agents.context_builder_agent import ContextBuilderAgent
            context_builder = ContextBuilderAgent(
                repo=self.repo,
                llm=self.llm,
                style_rag=self.style_rag,
                rag_prefetch=self.rag_prefetch,
            )

            # バイブルとプロットを取得
            bible = ctx.artifacts.get("bible")
            plots = ctx.artifacts.get("plots", [])
            plot = next((p for p in plots if getattr(p, "episode_number", 0) == ep_num), None)

            # 前話の章を取得
            prev_chapter = None
            if ep_num > 1:
                try:
                    prev_chapter = await self.repo.get_chapter(branch_id, ep_num - 1)
                except Exception:
                    pass

            writing_context = await context_builder.build_full_writing_context(
                book_id=book_id,
                branch_id=branch_id,
                ep_num=ep_num,
                target_word_count=target_word_count,
                style_tag=style_tag,
            )

            return AgentResult(
                next_agent=AgentName.WRITING,
                artifacts={
                    "writing_context": writing_context,
                },
            )
        except Exception as e:
            logger.exception("EasyModeContextBuilderSkill failed")
            return AgentResult(
                next_agent=None,
                artifacts={},
                error=f"Context building failed: {e}",
            )