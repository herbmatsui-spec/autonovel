# agents/bible.py
import logging
from typing import Any

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class BibleAgent(SkillAgent):
    """世界観設定・キャラクター設定の生成を担当するエージェント。
    LLM とプロンプトマネージャを利用して設定情報を生成する。
    """

    def __init__(self, repo: Any = None, llm: LLMService | None = None, prompt_manager: Any = None):
        super().__init__(repo=repo, llm=llm)
        self.prompt_manager = prompt_manager

    async def generate_bible(
        self, title: str, synopsis: str, target_eps: int, concept: str = "", **kwargs
    ) -> dict[str, Any]:
        if self.prompt_manager is None:
            raise ValueError("PromptManager is required for BibleAgent")
        world_prompt = self.prompt_manager.build_world_creation_prompt(
            genre=kwargs.get("genre", "fantasy"),
            keywords=kwargs.get("keywords", ""),
            response_schema=None,
            concept=concept,
            target_eps=target_eps,
        )
        world_result = await self.llm.generate_json(purpose="planning", prompt=world_prompt)
        world_data = world_result.get("metadata", {})
        return world_data

    async def execute(self, ctx: AgentContext) -> AgentResult:
        """スキル実行エントリーポイント。"""
        self.emit_event("bible.started", {
            "book_id": ctx.book_id,
            "title": ctx.artifacts.get("title"),
        })
        
        title = ctx.artifacts.get("title")
        synopsis = ctx.artifacts.get("synopsis", "")
        target_eps = ctx.artifacts.get("target_eps", 10)
        concept = ctx.artifacts.get("concept", "")
        genre = ctx.artifacts.get("genre", "fantasy")
        keywords = ctx.artifacts.get("keywords", "")

        if not title:
            self.emit_event("bible.error", {
                "book_id": ctx.book_id,
                "error": "title is required in artifacts",
            })
            return AgentResult(
                next_agent=None,
                artifacts={},
                error="title is required in artifacts",
            )

        bible_data = await self.generate_bible(
            title=title,
            synopsis=synopsis,
            target_eps=target_eps,
            concept=concept,
            genre=genre,
            keywords=keywords,
        )

        self.emit_event("bible.completed", {
            "book_id": ctx.book_id,
            "title": title,
        })
        
        return AgentResult(
            next_agent=AgentName.CONTEXT_BUILDER,
            artifacts={"bible": bible_data},
        )

    async def run(self, ctx: AgentContext) -> AgentResult:
        """Orchestrator 用エントリーポイント。execute をラップする。"""
        return await self.execute(ctx)
