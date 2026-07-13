import logging
from typing import Any, Dict

from src.agents.base import BaseAgent

logger = logging.getLogger(__name__)

class DiversityScorer(BaseAgent):
    """コンテンツの多様性スコアを算出するエージェント。"""

    async def score(self, content: str) -> Dict[str, Any]:
        words = content.split()
        unique = set(words)
        diversity = len(unique) / len(words) if words else 0.0
        return {"diversity": round(diversity, 4), "word_count": len(words), "unique_words": len(unique)}

    async def run(self, *args, **kwargs):
        content = kwargs.get("content", "")
        return await self.score(content)

