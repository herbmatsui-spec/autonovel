"""
src/agents/early_entertainment_checker.py
早期面白さ検証エージェント。

品質を評価せず、面白さのみを検証し、興味スコアを返す。
LLM推論結果のJSONパース失敗時は interest_score=0 のフォールバックを返す。
"""
from __future__ import annotations

import logging
from typing import Any

from src.models.entertainment_check import EntertainmentCheckResult

logger = logging.getLogger(__name__)


class EarlyEntertainmentChecker:
    """ラフプロット・冒頭500字による早期面白さ検証エージェント"""
    def __init__(self, llm: Any, prompt_manager: Any):
        self.llm = llm
        self.prompt_manager = prompt_manager

    async def check(self, rough_plot: str, opening_500_chars: str) -> EntertainmentCheckResult:
        """
        早期面白さ検証を実行し、EntertainmentCheckResult を返す。

        - LLM応答のJSONパース失敗時は interest_score=0 のフォールバック。
        - パース成功時はスコアを検証し、異常値は0に丸める。
        """
        if self.prompt_manager is None:
            return EntertainmentCheckResult(
                interest_score=0,
                physiological_reaction="無反応",
                would_continue_reading=False,
                feedback="prompt_managerが未設定",
            )

        try:
            prompt = await self.prompt_manager.build_early_entertainment_check_prompt(
                rough_plot=rough_plot,
                opening_500_chars=opening_500_chars,
            )
            result = await self.llm.generate_json(purpose="entertainment_check", prompt=prompt)
            metadata = result.get("metadata", {})

            raw_score = metadata.get("interest_score", 0)
            if not isinstance(raw_score, (int, float)) or raw_score < 0 or raw_score > 100:
                raw_score = 0
            raw_score = int(raw_score)

            return EntertainmentCheckResult(
                interest_score=raw_score,
                physiological_reaction=str(metadata.get("physiological_reaction", "無反応")),
                would_continue_reading=bool(metadata.get("would_continue_reading", False)),
                feedback=str(metadata.get("feedback", ""))[:300],
            )
        except Exception:
            logger.warning("早期面白さ検証に失敗、フォールバックを返します", exc_info=True)
            return EntertainmentCheckResult(
                interest_score=0,
                physiological_reaction="無反応",
                would_continue_reading=False,
                feedback="検証失敗",
            )
