"""6コマ要約漫画のプロンプト戦略。

コマ要約の生成は既存の `YonkomaPlanner`（LLM 版／ヒューリスティック版）を
**再利用**し、プロンプト本文も既存の `build_yonkoma_prompt` /
`apply_yonkoma_safety_modifier` に委譲する（ロジックの重複実装をしない）。
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.models.illustration import IllustrationRequest, IllustrationType
from src.services.illustration.strategies.base import PromptStrategy

logger = logging.getLogger(__name__)

# 既存仕様: 6コマ要約（起承転結 + 余韻）
DEFAULT_PANELS = 6
MIN_PANELS = 3
MAX_PANELS = 6

# シーン要約が無い場合のプレースホルダ（旧実装と同一文言）
PLACEHOLDER_SUMMARIES = [
    "(導入)",
    "(展開)",
    "(転換)",
    "(高潮)",
    "(余韻)",
    "(次回への引き)",
]


class Yonkoma6Strategy(PromptStrategy):
    """1話を6コマに要約した漫画シートのプロンプトを作る。"""

    illustration_type = IllustrationType.YONKOMA

    @staticmethod
    def clamp_panels(panels: Optional[int]) -> int:
        """コマ数を 3..6 に収める（既存仕様）。"""
        if panels is None:
            return DEFAULT_PANELS
        try:
            value = int(panels)
        except (TypeError, ValueError):
            return DEFAULT_PANELS
        return max(MIN_PANELS, min(value, MAX_PANELS))

    async def build_prompt_async(self, request: IllustrationRequest) -> str:
        """LLM 要約を必要とするため、非同期版でプロンプトを生成する。"""
        from src.services.illustration.prompts import build_yonkoma_prompt
        from src.services.illustration.scene_service import YonkomaPlanner

        panels = self.clamp_panels(getattr(request, "panels", DEFAULT_PANELS))
        text = (request.scene_text or "").strip()
        ctx = self._book_context(request)

        summaries: List[str]
        if text:
            planner = YonkomaPlanner()
            if self.llm is not None:
                try:
                    summaries = await planner.plan_with_llm(text, self.llm, panels=panels)
                except Exception as exc:  # noqa: BLE001
                    logger.warning("Yonkoma LLM planning failed in strategy: %s", exc)
                    summaries = planner.plan_heuristic(text, panels=panels)
            else:
                summaries = planner.plan_heuristic(text, panels=panels)
        else:
            summaries = list(PLACEHOLDER_SUMMARIES)[:panels]
            while len(summaries) < panels:
                summaries.append(PLACEHOLDER_SUMMARIES[-1])

        prompt = build_yonkoma_prompt(summaries, ctx, panels=panels)
        return self._apply_yonkoma_safety(prompt, request.safety_level)

    def build_prompt(self, request: IllustrationRequest) -> str:
        """同期版（LLM なし）。非同期経路では `build_prompt_async` を使うこと。"""
        from src.services.illustration.prompts import build_yonkoma_prompt
        from src.services.illustration.scene_service import YonkomaPlanner

        panels = self.clamp_panels(getattr(request, "panels", DEFAULT_PANELS))
        text = (request.scene_text or "").strip()
        ctx = self._book_context(request)

        if text:
            summaries = YonkomaPlanner().plan_heuristic(text, panels=panels)
        else:
            summaries = list(PLACEHOLDER_SUMMARIES)[:panels]
            while len(summaries) < panels:
                summaries.append(PLACEHOLDER_SUMMARIES[-1])

        prompt = build_yonkoma_prompt(summaries, ctx, panels=panels)
        return self._apply_yonkoma_safety(prompt, request.safety_level)


__all__ = [
    "DEFAULT_PANELS",
    "MAX_PANELS",
    "MIN_PANELS",
    "PLACEHOLDER_SUMMARIES",
    "Yonkoma6Strategy",
]
