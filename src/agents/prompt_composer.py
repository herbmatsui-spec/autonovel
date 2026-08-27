"""
prompt_composer.py - 執筆プロンプト構築ユーティリティ
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.agents.base import BaseAgent


class PromptComposer:
    """執筆プロンプトを構築するユーティリティクラス"""

    def __init__(self, agent: BaseAgent):
        """
        Args:
            agent: 親エージェント（プロンプトマネージャへのアクセスのために必要）
        """
        self.agent = agent

    def _build_erotic_prompt_section(self, context: Dict[str, Any]) -> str:
        """官能コンテキストが存在する場合、EroticSpecialist を用いて官能プロンプトセクションを生成する。"""
        erotic_intensity = context.get("erotic_intensity", 0)
        nsfw_enabled = context.get("nsfw_enabled", False) or context.get("enable_erotic", False)

        if not (erotic_intensity > 0 and nsfw_enabled):
            return ""

        try:
            from config.erotic_pacing import EroticCurve
            from config.erotic_parameters import EroticParameters
            from src.engine.prompts.erotic_specialist import EroticSpecialist

            sensory_weights = context.get("erotic_sensory_weights")
            pace_ratios = context.get("erotic_pace_ratios")
            metaphor_density = context.get("erotic_metaphor_density", 50)
            psychology_depth = context.get("erotic_psychology_depth", 50)
            use_video_patterns = context.get("erotic_use_video_patterns", True)

            kwargs: Dict[str, Any] = {
                "enabled": True,
                "base_intensity": erotic_intensity,
                "metaphor_density": metaphor_density,
                "psychology_depth": psychology_depth,
                "use_video_patterns": use_video_patterns,
            }
            if sensory_weights:
                kwargs["sensory_weights"] = sensory_weights
            if pace_ratios:
                kwargs["pace_ratios"] = pace_ratios

            params = EroticParameters(**kwargs)
            specialist = EroticSpecialist()
            curve = EroticCurve.create_from_parameters(params)
            peak_beat = curve.get_peak_beat()
            context["consent_state"] = peak_beat.consent_state if peak_beat else "implicit"
            return specialist.build_scene_prompt(curve, context, params)
        except Exception as e:
            if hasattr(self.agent, "logger") and self.agent.logger is not None:
                self.agent.logger.warning(f"Failed to build erotic prompt section: {e}")
            return ""

    async def compose_writing_prompt(
        self,
        book_id: int,
        ep_num: int,
        context: Dict[str, Any],
    ) -> str:
        """執筆用プロンプトを構築する。

        Args:
            book_id: 書籍ID
            ep_num: エピソード番号
            context: プロット情報、キャラ設定、世界設定などを含む辞書

        Returns:
            構築されたプロンプト文字列
        """
        if getattr(self.agent, "prompt_manager", None) is None:
            raise ValueError("PromptManager is not injected into WritingAgent")

        plot_data = context.get("plot", {})
        if not plot_data.get("detailed_blueprint"):
            if hasattr(self.agent, "logger") and self.agent.logger is not None:
                self.agent.logger.warning(
                    f"Ep.{ep_num}: detailed_blueprint is empty. Writing may be low quality."
                )

        script_text = context.get("script", "")
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
        )

        erotic_section = self._build_erotic_prompt_section(context)
        if erotic_section:
            prompt = f"{prompt}\n\n{erotic_section}"

        return prompt
