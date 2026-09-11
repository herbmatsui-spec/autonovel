# src/agents/skills/v1/easy_mode_illustration.py
"""easy_mode 専用 IllustrationSkill - 簡易挿絵生成"""
from __future__ import annotations

import logging
from typing import Any

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName

logger = logging.getLogger(__name__)


class EasyModeIllustrationSkill(SkillAgent):
    """かんたんモード用挿絵生成スキル（簡易版）"""

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
        """簡易挿絵生成を実行（スキップ可能）"""
        try:
            # easy_mode では挿絵生成をスキップして次へ
            # 必要に応じて簡易版 IllustrationAgent を呼び出す
            
            drafted_text = ctx.artifacts.get("drafted_text", "")
            book_context = {
                "title": ctx.artifacts.get("title", ""),
                "genre": ctx.artifacts.get("genre", ""),
            }

            # 簡易版: イラスト生成をスキップ（空リスト返却）
            # 本格的な実装が必要な場合は IllustrationAgent を呼び出す
            illustrations = []

            return AgentResult(
                next_agent=AgentName.MARKETING,
                artifacts={
                    "illustrations": illustrations,
                },
            )
        except Exception as e:
            logger.exception("EasyModeIllustrationSkill failed")
            return AgentResult(
                next_agent=None,
                artifacts={},
                error=f"Illustration failed: {e}",
            )