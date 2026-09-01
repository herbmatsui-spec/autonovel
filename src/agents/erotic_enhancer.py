"""
erotic_enhancer.py - 官能強化ユーティリティ
"""

from __future__ import annotations

from typing import Any, Dict

from src.agents.base import BaseAgent


class EroticEnhancer:
    """官能コンテンツを強化するユーティリティクラス"""

    def __init__(self, agent: BaseAgent):
        """
        Args:
            agent: 親エージェント（エロティック機能へのアクセスのために必要）
        """
        self.agent = agent

    async def enhance_erotic_content(
        self,
        prompt: str,
        result: str,
        context: Dict[str, Any],
    ) -> str:
        """官能コンテンツを強化する。

        Args:
            prompt: 元のプロンプト
            result: LLMによって生成された結果
            context: コンテキスト情報

        Returns:
            � 強化された結果文字列
        """
        erotic_intensity = context.get("erotic_intensity", 0)
        nsfw_enabled = context.get("nsfw_enabled", False)

        if not (erotic_intensity > 0 and nsfw_enabled):
            return result

        specialist = None
        params = None

        try:
            from config.erotic_pacing import EroticCurve
            from config.erotic_parameters import EroticParameters
            from src.engine.prompts.erotic_specialist import EroticSpecialist

            sensory_weights = context.get("erotic_sensory_weights")
            pace_ratios = context.get("erotic_pace_ratios")
            metaphor_density = context.get("erotic_metaphor_density", 50)
            psychology_depth = context.get("erotic_psychology_depth", 50)
            use_video_patterns = context.get("erotic_use_video_patterns", True)

            params = EroticParameters(
                enabled=True,
                base_intensity=erotic_intensity,
                sensory_weights=sensory_weights if sensory_weights else None,
                pace_ratios=pace_ratios if pace_ratios else None,
                metaphor_density=metaphor_density,
                psychology_depth=psychology_depth,
                use_video_patterns=use_video_patterns,
            )

            specialist = EroticSpecialist()
            curve = EroticCurve.create_from_parameters(params)
            peak_beat = curve.get_peak_beat()
            context["consent_state"] = peak_beat.consent_state if peak_beat else "implicit"
            erotic_prompt = specialist.build_scene_prompt(curve, context, params)
            prompt = prompt + "\n\n" + erotic_prompt
        except Exception as e:
            if hasattr(self.agent, "logger") and self.agent.logger is not None:
                self.agent.logger.warning(f"EroticSpecialist delegation failed, falling back: {e}")
            params = None

        # LLM再生成（プロンプトが変更された場合）
        if specialist and erotic_intensity > 0 and nsfw_enabled and prompt.endswith(erotic_prompt):
            try:
                result = await self.agent.llm.generate_text(
                    purpose="writing",
                    prompt=prompt,
                    system_instruction=None,
                    temperature=0.7,
                )
                if hasattr(result, "story_content"):
                    result = result.story_content
            except Exception as e:
                if hasattr(self.agent, "logger") and self.agent.logger is not None:
                    self.agent.logger.warning(f"LLM regeneration failed: {e}")

        # メタファーフィルタ適用
        if specialist and erotic_intensity > 0 and nsfw_enabled:
            try:
                result = specialist.metaphor_filter(result, erotic_intensity)
            except Exception as e:
                if hasattr(self.agent, "logger") and self.agent.logger is not None:
                    self.agent.logger.warning(f"metaphor_filter failed: {e}")

        # アフターグロウ評価
        if specialist and erotic_intensity > 0 and nsfw_enabled:
            try:
                from src.services.erotic_afterglow_evaluator import AfterglowEvaluator

                evaluator = AfterglowEvaluator()
                afterglow_candidate = result[len(result) * 3 // 4 :]
                afterglow_ok, afterglow_issues = evaluator.evaluate(afterglow_candidate)
                if not afterglow_ok:
                    if hasattr(self.agent, "logger") and self.agent.logger is not None:
                        self.agent.logger.warning(
                            f"Episode {context.get('ep_num', '?')} afterglow quality issues: {afterglow_issues}. "
                            "Consider regeneration or supplementation."
                        )
            except Exception as e:
                if hasattr(self.agent, "logger") and self.agent.logger is not None:
                    self.agent.logger.warning(f"Afterglow evaluation failed: {e}")

        return result
