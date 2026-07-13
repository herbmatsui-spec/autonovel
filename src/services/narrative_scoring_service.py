import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

class NarrativeScoringService:
    """ナラティブスコアリングサービス（簡易実装）"""
    def __init__(self, llm: Any, prompt_manager: Any):
        self.llm = llm
        self.prompt_manager = prompt_manager

    async def score(self, content: str, schema: Any) -> Dict[str, Any]:
        if self.prompt_manager is None:
            return {"score": 0.0, "feedback": "OK"}
        prompt = self.prompt_manager.build_critique_quality_prompt(
            book_title="",
            summary_data_json=content,
        )
        result = await self.llm.generate_json(purpose="audit", prompt=prompt)
        metadata = result.get("metadata", {})
        return metadata
