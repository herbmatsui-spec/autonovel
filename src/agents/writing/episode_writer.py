from typing import Any

from src.agents.base import BaseAgent
from src.agents.context_builder_agent import ContextBuilderAgent
from src.agents.erotic_enhancer import EroticEnhancer
from src.agents.orchestrator import AgentContext
from src.agents.prompt_composer import PromptComposer
from src.services.llm_service import LLMService


class EpisodeWriter(BaseAgent):
    def __init__(
        self,
        llm: LLMService,
        context_builder: ContextBuilderAgent,
        repo: Any = None,
        style_rag: Any = None,
        rag_prefetch: Any = None,
    ):
        super().__init__(repo=repo, llm=llm, style_rag=style_rag, rag_prefetch=rag_prefetch)
        self.context_builder = context_builder

    async def build_context(
        self,
        book_id: int,
        branch_id: int,
        ep_num: int,
        target_word_count: int,
        style_tag: str | None = None,
    ) -> dict[str, Any]:
        """執筆に必要な完全なコンテキストを構築する。"""
        ctx = AgentContext(
            book_id=book_id,
            branch_id=branch_id,
            ep_num=ep_num,
            artifacts={
                "target_word_count": target_word_count,
                "style_tag": style_tag,
            },
        )
        result = await self.context_builder.execute(ctx)
        return result.artifacts.get("writing_context", {})

    async def write(self, book_id: int, ep_num: int, context: dict[str, Any]) -> str:
        """
        エピソード本文を生成し、文字列で返す。
        :param book_id: 書籍ID
        :param ep_num: エピソード番号
        :param context: プロット情報、キャラ設定、世界設定などを含む辞書
        :return: 生成された本文（文字列）
        """
        # プロンプトを構築
        prompt_composer = PromptComposer(self)
        prompt = await prompt_composer.compose_writing_prompt(book_id, ep_num, context)

        # 初期結果を生成
        result = await self.llm.generate_text(
            purpose="writing",
            prompt=prompt,
            system_instruction=None,
            temperature=0.7,
        )
        if hasattr(result, "story_content"):
            result = result.story_content

        # エロティックコンテンツを強化
        erotic_enhancer = EroticEnhancer(self)
        result = erotic_enhancer.enhance_erotic_content(prompt, result, context)

        return str(result)
