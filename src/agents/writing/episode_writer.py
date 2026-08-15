from typing import Any, Dict, Optional

from src.agents.context_builder import ContextBuilder
from src.agents.erotic_enhancer import EroticEnhancer
from src.agents.prompt_composer import PromptComposer
from src.services.llm_service import LLMService


class EpisodeWriter:
    def __init__(self, llm: LLMService, context_builder: ContextBuilder):
        self.llm = llm
        self.context_builder = context_builder

    async def build_context(
        self,
        book_id: int,
        branch_id: int,
        ep_num: int,
        target_word_count: int,
        style_tag: Optional[str] = None,
    ) -> Dict[str, Any]:
        """執筆に必要な完全なコンテキストを構築する。"""
        return await self.context_builder.build_full_writing_context(
            book_id, branch_id, ep_num, target_word_count, style_tag
        )

    async def write(self, book_id: int, ep_num: int, context: Dict[str, Any]) -> str:
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
        result = await erotic_enhancer.enhance_erotic_content(prompt, result, context)

        return str(result)
