"""
prompt_composer.py - プロンプト構�築ユーティリティ
"""

from __future__ import annotations

from typing import Any, Dict, Optional

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
        context: Dict[str, Any],
    ) -> str:
        """�執�筆用プロンプトを構�築する。
        
        Args:
            book_id: 書籍ID
            ep_num: エピソード番号
            context: プロット情報、キャラ設定、世界設定などを含む�辞書
            
        Returns:
            �� 構�築されたプロンプト文字列
        """
        if getattr(self.agent, 'prompt_manager', None) is None:
            raise ValueError("PromptManager is not injected into WritingAgent")

        plot_data = context.get("plot", {})
        if not plot_data.get("detailed_blueprint"):
            if hasattr(self.agent, 'logger'):
                self.agent.logger.warning(f"Ep.{ep_num}: detailed_blueprint is empty. Writing may be low quality.")

        script_text = context.get("script", "")
        prompt = await getattr(self.agent, 'prompt_manager').build_final_writing_prompt(
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
        )
        
        return prompt
