"""
services/hook_diagnoser.py - 章末フック強度診断・修正案生成サービス

既存の QualityScorer.score_hook_retention を利用して各章のフック保持率を
算出し、閾値を下回る章の修正案を LLM で生成する。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.services.quality_scorer import QualityScorer

logger = logging.getLogger(__name__)

HOOK_THRESHOLD = 0.7


class HookDiagnoser:
    """章末フックの診断と修正案生成を行うサービス。"""

    def __init__(self, llm_service: Optional[Any] = None):
        self.scorer = QualityScorer()
        self._llm = llm_service

    async def diagnose(self, chapters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """各章のフックスコアを算出し、弱いフックをフラグ付けする。"""
        results: List[Dict[str, Any]] = []
        for ch in chapters:
            text = ch.get("content") or ""
            ep_num = ch.get("ep_num")
            try:
                score = await self.scorer.score_hook_retention(text)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"hook scoring failed for ep {ep_num}: {exc}")
                score = 0.0
            results.append(
                {
                    "ep_num": ep_num,
                    "title": ch.get("title"),
                    "hook_score": round(score, 3),
                    "is_weak": score < HOOK_THRESHOLD,
                }
            )
        return results

    async def detect_weak_hooks(self, chapters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """閾値を下回る章のみを返す。"""
        return [r for r in await self.diagnose(chapters) if r["is_weak"]]

    async def generate_hook_fix(self, chapter: Dict[str, Any], api_key: str) -> str:
        """弱いフックの章に対し、章末を改善する修正案を生成する。"""
        if self._llm is None:
            from src.services.llm_service import LLMService

            self._llm = LLMService(api_key=api_key)

        text = chapter.get("content") or ""
        prompt = (
            "以下の小説の章について、読者の続きを読みたい欲求（フック）を"
            "強めるための「章末の書き換え案（最後の2〜3文のみ）」を提案してください。\n"
            "既存の文脈・トーンを崩さず、未解決の問いや予兆を際立たせてください。\n\n"
            f"【章本文（抜粋）】\n{text[-1500:]}"
        )
        try:
            return await self._llm.generate_text(purpose="writing", prompt=prompt, temp=0.8)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"hook fix generation failed: {exc}")
            return ""
