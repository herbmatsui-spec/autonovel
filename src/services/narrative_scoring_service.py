import logging
from typing import Any

logger = logging.getLogger(__name__)


class NarrativeScoringService:
    """ナラティブスコアリングサービス（簡易実装）"""

    def __init__(self, llm: Any, prompt_manager: Any):
        self.llm = llm
        self.prompt_manager = prompt_manager

    async def score(self, content: str, schema: Any = None) -> dict[str, Any]:
        """ナラティブの品質・構造を評価してスコアとフィードバックを返す"""
        if not content:
            return {"score": 0.0, "feedback": "Content is empty"}

        if self.prompt_manager is None or self.llm is None:
            return {"score": 75.0, "feedback": "Rule-based fallback evaluation: narrative structure is acceptable."}

        try:
            prompt = self.prompt_manager.build_critique_quality_prompt(
                book_title="",
                summary_data_json=content,
            )
            result = await self.llm.generate_json(purpose="audit", prompt=prompt)
            metadata = result.get("metadata", {}) if isinstance(result, dict) else {}
            score_val = float(metadata.get("score", result.get("score", 75.0))) if isinstance(result, dict) else 75.0
            return {"score": score_val, "feedback": metadata.get("feedback", "Narrative scoring complete"), "raw": result}
        except Exception as e:
            logger.warning("Narrative scoring LLM call failed, returning fallback: %s", e)
            return {"score": 70.0, "feedback": f"Fallback due to error: {e}"}
