"""
erotic_enhancer.py - 官能後処理・品質向上ユーティリティ
"""

from __future__ import annotations

from typing import Any, Dict

from src.agents.base import BaseAgent


class EroticEnhancer:
    """官能コンテンツの後処理（メタファーフィルタ・品質評価）を行うユーティリティクラス"""

    def __init__(self, agent: BaseAgent):
        """
        Args:
            agent: 親エージェント
        """
        self.agent = agent

    def post_process_erotic_content(
        self,
        text: str,
        context: Dict[str, Any],
    ) -> str:
        """生成済みテキストに対して官能メタファーフィルタと品質評価を適用する。

        Args:
            text: LLMによって生成されたエピソード本文
            context: コンテキスト情報

        Returns:
            後処理適用後の本文文字列
        """
        erotic_intensity = context.get("erotic_intensity", 0)
        nsfw_enabled = context.get("nsfw_enabled", False) or context.get("enable_erotic", False)

        if not (erotic_intensity > 0 and nsfw_enabled):
            return text

        result = text

        # 1. メタファーフィルタ適用
        try:
            from src.engine.prompts.erotic_specialist import EroticSpecialist

            specialist = EroticSpecialist()
            result = specialist.metaphor_filter(result, erotic_intensity)
        except Exception as e:
            if hasattr(self.agent, "logger") and self.agent.logger is not None:
                self.agent.logger.warning(f"metaphor_filter failed: {e}")

        # 2. アフターグロウ（余韻）評価
        try:
            from src.services.erotic_afterglow_evaluator import AfterglowEvaluator

            evaluator = AfterglowEvaluator()
            afterglow_candidate = result[len(result) * 3 // 4 :]
            afterglow_ok, afterglow_issues = evaluator.evaluate(afterglow_candidate)
            if not afterglow_ok:
                if hasattr(self.agent, "logger") and self.agent.logger is not None:
                    self.agent.logger.warning(
                        f"Episode {context.get('ep_num', '?')} afterglow quality issues: {afterglow_issues}"
                    )
        except Exception as e:
            if hasattr(self.agent, "logger") and self.agent.logger is not None:
                self.agent.logger.warning(f"Afterglow evaluation failed: {e}")

        return result

    async def enhance_erotic_content(
        self,
        prompt: str,
        result: str,
        context: Dict[str, Any],
    ) -> str:
        """後方互換用メソッド。内部で post_process_erotic_content を実行する。"""
        return self.post_process_erotic_content(result, context)
