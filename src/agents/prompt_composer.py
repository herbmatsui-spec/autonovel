"""
prompt_composer.py - プロンプト構�築ユーティリティ
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent


class PromptComposer:
    """プロンプトを構���築するユーティリティクラス"""

    def __init__(self, agent: BaseAgent):
        """
        Args:
            agent: 親エージェント（プロンプトマネージャへのアクセスのために必要）
        """
        self.agent = agent

    async def compose_writing_prompt(
        self,
        book_id: int,
        ep_num: int,
        context: dict[str, Any],
    ) -> str:
        """�執�筆用プロンプトを構�築する。

        Args:
            book_id: 書籍ID
            ep_num: エピソード番号
            context: プロット情報、キャラ設定、世界設定などを含む�辞書

        Returns:
            �� 構�築されたプロンプト文字列
        """
        if getattr(self.agent, "prompt_manager", None) is None:
            raise ValueError("PromptManager is not injected into WritingAgent")

        plot_data = context.get("plot", {})
        if not plot_data.get("detailed_blueprint"):
            if hasattr(self.agent, "logger"):
                self.agent.logger.warning(
                    f"Ep.{ep_num}: detailed_blueprint is empty. Writing may be low quality."
                )

        script_text = context.get("script", "")
        # Get foreshadowing context if context_retriever is available on the agent
        foreshadowing_context = ""
        context_retriever = getattr(self.agent, "context_retriever", None)
        if context_retriever and book_id is not None:
            plot_data = context.get("plot", {})
            plot_outline = plot_data.get("detailed_blueprint", "")
            if not plot_outline:
                plot_outline = plot_data.get("summary", "")
            character_names = []  # We don't have character names easily, so pass empty list
            try:
                context_dict = context_retriever.retrieve_writing_context(
                    book_id=book_id,
                    current_ep=ep_num,
                    plot_outline=plot_outline,
                    character_names=character_names,
                )
                foreshadowing_context = context_retriever.format_context_for_prompt(context_dict)
            except Exception as e:
                if hasattr(self.agent, "logger"):
                    self.agent.logger.warning(
                        f"Ep.{ep_num}: Failed to get foreshadowing context: {e}"
                    )
                foreshadowing_context = ""
        prompt = await getattr(self.agent, "prompt_manager").build_final_writing_prompt(
            ep_num=ep_num,
            plot_data=plot_data,
            script_text=script_text,
            target_word_count=context.get("target_word_count", 2000),
            book_id=book_id,
            char_static_ctx=context.get("char_static_ctx", ""),
            char_dynamic_ctx=context.get("char_dynamic_ctx", ""),
            prev_ctx=context.get("prev_ctx", ""),
            pov_character_name=context.get("pov_character_name", ""),
            dialogue_profiles=context.get("dialogue_profiles", {}),
            density_level=context.get("density_level", "Standard"),
            style_tag=context.get("style_tag"),
            foreshadowing_context=foreshadowing_context,
        )

        regeneration_directive = context.get("regeneration_directive")
        if regeneration_directive:
            prompt = (
                f"==================================================\n"
                f"【最優先・再生成修正ディレクティブ】\n"
                f"前回の審査で指摘された以下の問題点・Actionable Diffsを最優先で反映して執筆してください:\n\n"
                f"{regeneration_directive}\n"
                f"==================================================\n\n"
                + prompt
            )

        return prompt
