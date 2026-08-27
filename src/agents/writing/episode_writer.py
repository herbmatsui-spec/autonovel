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
        # 官能モード判定
        erotic_intensity = context.get("erotic_intensity", 0)
        is_nsfw = bool(
            erotic_intensity > 0
            and (context.get("nsfw_enabled", False) or context.get("enable_erotic", False))
        )

        # プロンプトを構築（官能プロンプトも事前結合）
        prompt_composer = PromptComposer(self)
        prompt = await prompt_composer.compose_writing_prompt(book_id, ep_num, context)

        # テキスト生成（シングルパス）
        result = await self.llm.generate_text(
            purpose="writing",
            prompt=prompt,
            system_instruction=None,
            temperature=0.7,
            nsfw_mode=is_nsfw,
        )
        if hasattr(result, "story_content"):
            result = result.story_content

        # 官能後処理（メタファーフィルタ・アフターグロウ評価）
        erotic_enhancer = EroticEnhancer(self)
        result = erotic_enhancer.post_process_erotic_content(str(result), context)

        return str(result)
