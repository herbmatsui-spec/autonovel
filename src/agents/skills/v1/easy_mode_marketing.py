# src/agents/skills/v1/easy_mode_marketing.py
"""easy_mode 専用 MarketingSkill - 簡易納品パッケージ生成"""
from __future__ import annotations

import logging
from typing import Any

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult

logger = logging.getLogger(__name__)


class EasyModeMarketingSkill(SkillAgent):
    """かんたんモード用納品パッケージ生成スキル"""

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
        """簡易納品パッケージ生成を実行"""
        try:
            book_id = ctx.book_id
            drafted_text = ctx.artifacts.get("drafted_text", "")
            illustrations = ctx.artifacts.get("illustrations", [])
            bible = ctx.artifacts.get("bible")
            plots = ctx.artifacts.get("plots", [])

            # MarketingAgent を使用して ZIP 生成
            from src.agents.marketing import MarketingAgent
            marketing_agent = MarketingAgent(
                repo=self.repo,
                prompt_manager=self.pm,
                llm=self.llm,
            )

            book_data = {
                "title": ctx.artifacts.get("title", "無題"),
                "genre": ctx.artifacts.get("genre", "ファンタジー"),
                "chapters": [
                    {
                        "ep_num": ep_num,
                        "title": f"第{ep_num}話",
                        "content": drafted_text,
                    }
                ],
                "characters": getattr(bible, "characters", []) if bible else [],
                "plots": [
                    {
                        "ep_num": getattr(p, "episode_number", 0),
                        "title": getattr(p, "title", ""),
                        "one_line_summary": getattr(p, "summary", ""),
                    }
                    for p in plots
                ] if plots else [],
                "bible_settings": getattr(bible, "model_dump", lambda: {})() if bible else {},
            }

            zip_bytes, zip_filename = await marketing_agent.create_export_package(
                book_id=book_id,
                book_data=book_data,
            )

            return AgentResult(
                next_agent=None,  # 終了
                artifacts={
                    "zip_data": zip_bytes,
                    "zip_filename": zip_filename,
                },
            )
        except Exception as e:
            logger.exception("EasyModeMarketingSkill failed")
            return AgentResult(
                next_agent=None,
                artifacts={},
                error=f"Marketing failed: {e}",
            )