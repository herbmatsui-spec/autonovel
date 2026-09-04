# agents/planning.py
import logging
from typing import Any

from src.agents.skill_base import SkillAgent
from src.agents.orchestrator import AgentContext, AgentResult, AgentName
from src.models.plot import ArcList
from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class PlanningAgent(SkillAgent):
    """企画・プロット立案を担当するエージェント。
    LLM にアーク生成プロンプトを投げ、JSON 形式でアーク案を受け取る。
    """

    def __init__(self, repo: Any = None, llm: LLMService | None = None, prompt_manager: Any = None):
        super().__init__(repo=repo, llm=llm)
        self.prompt_manager = prompt_manager

    async def generate_arcs(
        self,
        title: str,
        synopsis: str,
        target_eps: int,
        start_ep: int = 1,
        **kwargs: Any,
    ) -> ArcList:
        """作品のアーク構成を生成する。

        Args:
            title: 作品タイトル
            synopsis: あらすじ
            target_eps: 生成対象の総話数
            start_ep: 再構築時の開始話数（デフォルト1 = 全文生成）
            **kwargs: その他のプロンプト引数

        Returns:
            生成されたアークリスト (ArcList)

        Raises:
            RuntimeError: アーク生成に失敗した場合
        """
        # 再構築（start_ep > 1）の場合は、生成する話数を開始話数で相殺し、
        # プロンプトにも「第N話以降」の指示を合成する。
        effective_eps = max(target_eps - start_ep + 1, 1)
        if start_ep > 1:
            synopsis = (
                f"【第{start_ep}話からの再構築】\n"
                f"以下は第{start_ep}話以降の物語構成である。\n"
                f"{synopsis}"
            )

        prompt = self.prompt_manager.build_arc_generation_prompt(
            title=title,
            synopsis=synopsis,
            target_eps=effective_eps,
            start_ep=start_ep,
            **kwargs,
        )
        result = await self.llm.generate_json(
            purpose="planning",
            prompt=prompt,
            response_schema=None,  # 必要に応じて Pydantic スキーマを指定
        )
        if not result.get("success"):
            raise RuntimeError("Arc generation failed")

        metadata = result.get("metadata", {})
        # プロンプト生成時の都合で start_ep が 1 に丸められているため、
        # 各アークの話数オフセットを start_ep に合わせて補正する。
        if start_ep > 1:
            metadata = self._shift_arcs_start_ep(metadata, start_ep)

        return ArcList.model_validate(metadata)

    @staticmethod
    def _shift_arcs_start_ep(metadata: Any, start_ep: int) -> Any:
        """生成されたアークの話数を start_ep ベースに補正する."""
        if not isinstance(metadata, dict):
            return metadata
        arcs = metadata.get("arcs")
        if not isinstance(arcs, list):
            return metadata
        for arc in arcs:
            if isinstance(arc, dict):
                for key in ("start_ep", "end_ep"):
                    if key in arc and isinstance(arc[key], int):
                        arc[key] = arc[key] + (start_ep - 1)
        return metadata

    async def execute(self, ctx: AgentContext) -> AgentResult:
        """スキル実行エントリーポイント。run から呼ばれる。"""
        self.emit_event("planning.started", {
            "book_id": ctx.book_id,
            "title": ctx.artifacts.get("title"),
        })
        
        title = ctx.artifacts.get("title")
        synopsis = ctx.artifacts.get("synopsis", "")
        target_eps = ctx.artifacts.get("target_eps", 10)
        start_ep = ctx.artifacts.get("start_ep", 1)

        if not title:
            self.emit_event("planning.error", {
                "book_id": ctx.book_id,
                "error": "title is required in artifacts",
            })
            return AgentResult(
                next_agent=None,
                artifacts={},
                error="title is required in artifacts",
            )

        arcs = await self.generate_arcs(
            title=title,
            synopsis=synopsis,
            target_eps=target_eps,
            start_ep=start_ep,
        )

        self.emit_event("planning.completed", {
            "book_id": ctx.book_id,
            "arc_count": len(arcs.arcs) if arcs.arcs else 0,
        })
        
        return AgentResult(
            next_agent=AgentName.PLOT,
            artifacts={"arcs": arcs.model_dump()},
        )

    async def run(self, ctx: AgentContext) -> AgentResult:
        """Orchestrator 用エントリーポイント。execute をラップする。"""
        return await self.execute(ctx)
