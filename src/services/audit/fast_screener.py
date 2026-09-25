"""
High-speed screener for early exit in audit pipeline.
Uses lightweight heuristics and optional LLM to quickly determine if text passes basic quality thresholds.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Tuple

logger = logging.getLogger(__name__)


class FastScreener:
    """
    A high-speed screener that evaluates basic quality thresholds.
    Checks length, sentence ending diversity, basic novel formatting, and optional LLM screening.
    """

    def __init__(self, threshold: float = 70.0, llm_client: Any = None):
        """
        Initialize the screener with a quality threshold.
        Args:
            threshold: Score above which the text is considered passing (0-100 scale).
            llm_client: Optional LLM client for advanced rapid screening.
        """
        self.threshold = threshold
        self.llm_client = llm_client

    async def screen(self, text: str) -> Tuple[float, bool]:
        """
        Screen the text and return a score and whether it passes the threshold.
        Args:
            text: The text to screen.
        Returns:
            A tuple (score, passed) where score is a float (0-100) and passed is bool.
        """
        if not text or not text.strip():
            return 0.0, False

        score = 100.0
        cleaned = text.strip()

        # 1. Length check: Minimum 500 characters for a standard scene / episode
        if len(cleaned) < 200:
            score -= 30.0
        elif len(cleaned) < 500:
            score -= 10.0

        # 2. Check for empty paragraphs or broken formatting
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if len(lines) < 3:
            score -= 20.0

        # 3. Sentence ending repetition check (e.g. 4+ consecutive sentences ending with 'た。')
        sentences = re.split(r'[。！？\n]', cleaned)
        valid_sentences = [s.strip() for s in sentences if len(s.strip()) > 3]
        if len(valid_sentences) >= 4:
            ta_endings = 0
            max_consecutive_ta = 0
            for s in valid_sentences:
                if s.endswith("た") or s.endswith("だ"):
                    ta_endings += 1
                    max_consecutive_ta = max(max_consecutive_ta, ta_endings)
                else:
                    ta_endings = 0
            if max_consecutive_ta >= 4:
                score -= 15.0

        # 4. Optional lightweight LLM check
        if self.llm_client is not None:
            try:
                # If LLM screening is available, invoke lightweight screening
                prompt = (
                    f"次の文章の品質を100点満点で評価し、数字のみを出力してください。\n"
                    f"文章:\n{cleaned[:300]}"
                )
                if hasattr(self.llm_client, "generate_async"):
                    res = await self.llm_client.generate_async(prompt)
                    match = re.search(r"\d+", str(res))
                    if match:
                        llm_score = float(match.group(0))
                        score = (score * 0.4) + (llm_score * 0.6)
            except Exception as e:
                logger.debug(f"FastScreener LLM call failed: {e}")

        final_score = max(0.0, min(100.0, score))
        passed = final_score >= self.threshold
        return final_score, passed
