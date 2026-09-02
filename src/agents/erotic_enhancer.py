"""
erotic_enhancer.py - 官能強化ユーティリティ (GraphRAG 心理・関係性パラメータ連動対応)
"""

from __future__ import annotations

from typing import Any

from src.agents.base import BaseAgent


class EroticEnhancer:
    """官能コンテンツを強化するユーティリティクラス (GraphRAG連携)"""

    def __init__(self, agent: BaseAgent):
        """
        Args:
            agent: 親エージェント（エロティック機能へのアクセスのために必要）
        """
        self.agent = agent

    def _resolve_graphrag_parameters(self, context: dict[str, Any]) -> dict[str, Any]:
        """GraphRAG の登場人物関係性に基づいて官能パラメーターを動的に調整・最適化する."""
        params_override = {}
        graph_context = context.get("graph_context", "")
        relationship_type = context.get("relationship_type", "").upper()

        # 敵対・背徳的関係性 (HATES / ENEMY / RIVAL)
        if "HATES" in relationship_type or "敵対" in graph_context or "嫌悪" in graph_context:
            params_override["psychology_depth"] = max(context.get("erotic_psychology_depth", 50), 85)
            params_override["default_consent"] = "implicit"
            params_override["pace_ratios"] = {"intro": 0.4, "escalation": 0.4, "climax": 0.2}
        # 主従・支配関係 (MASTER_SERVANT / 支配)
        elif "MASTER" in relationship_type or "主従" in graph_context or "支配" in graph_context:
            params_override["psychology_depth"] = max(context.get("erotic_psychology_depth", 50), 80)
            params_override["metaphor_density"] = 65
        # 友愛・両想い (LOVES / ALLY_OF / 恋人)
        elif "LOVES" in relationship_type or "恋人" in graph_context or "愛" in graph_context:
            params_override["psychology_depth"] = context.get("erotic_psychology_depth", 60)
            params_override["default_consent"] = "mutual"
            params_override["sensory_weights"] = {"touch": 1.2, "breath": 1.2, "gaze": 1.1}

        return params_override

    async def enhance_erotic_content(
        self,
        prompt: str,
        result: str,
        context: dict[str, Any],
    ) -> str:
        """官能コンテンツを強化する (GraphRAG 心理連携)。

        Args:
            prompt: 元のプロンプト
            result: LLMによって生成された結果
            context: コンテキスト情報

        Returns:
            強化された結果文字列
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

            # GraphRAG 由来のパラメータ自動補正
            overrides = self._resolve_graphrag_parameters(context)

            sensory_weights = overrides.get("sensory_weights") or context.get("erotic_sensory_weights")
            pace_ratios = overrides.get("pace_ratios") or context.get("erotic_pace_ratios")
            metaphor_density = overrides.get("metaphor_density") or context.get("erotic_metaphor_density", 50)
            psychology_depth = overrides.get("psychology_depth") or context.get("erotic_psychology_depth", 50)
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
            default_consent = overrides.get("default_consent", "implicit")
            context["consent_state"] = peak_beat.consent_state if peak_beat else default_consent
            
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
