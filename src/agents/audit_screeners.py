"""audit.py から分離されたプロット・能力スクリーニングクラス群"""
from __future__ import annotations

import logging
from typing import Any

from src.services.llm_service import LLMService

logger = logging.getLogger(__name__)


class FastPlotScreener:
    """プロット快速スクリーニング。Gemini にプロットの妥当性を検証させる。"""

    def __init__(self, llm: LLMService, prompt_manager: Any):
        self.llm = llm
        self.prompt_manager = prompt_manager

    async def screen_plot(self, blueprint: str) -> tuple[bool, str]:
        prompt = self.prompt_manager.build_fast_plot_screen_prompt(blueprint)
        result = await self.llm.generate_json(purpose="audit", prompt=prompt)
        metadata = result.get("metadata", {})
        return metadata.get("is_valid", True), metadata.get("feedback", "OK")


class AbilityConsistencyChecker:
    """能力整合性チェック"""

    def __init__(self, llm: LLMService, prompt_manager: Any = None):
        self.llm = llm
        self.prompt_manager = prompt_manager

    async def audit_ability_consistency(
        self, blueprint: str, settings_json: str, characters_json: str
    ) -> tuple[bool, str, str]:
        if self.prompt_manager is None:
            return True, "OK", ""
        prompt = self.prompt_manager.build_ability_audit_prompt(
            blueprint, settings_json, characters_json
        )
        result = await self.llm.generate_json(purpose="audit", prompt=prompt)
        metadata = result.get("metadata", {})
        return (
            metadata.get("is_consistent", True),
            metadata.get("feedback", "OK"),
            metadata.get("suggestions", ""),
        )
