"""Unit test for commercial score correlation utility.
The test uses a mock fetch list and a mock LLM that returns pre‑defined scores.
It verifies that the Pearson correlation between the artificial bookmark
ranking (high, medium, low) and the supplied commercial scores is close to 1.
"""

import asyncio
import json
import sys
from typing import List, Dict

# Ensure the project root is on PYTHONPATH for imports
sys.path.append(r'E:\\sda')

from src.backend.kakuyomu.commercial_validation import compute_correlation

# ---------------------------------------------------------------------------
# Mock LLM – returns a score based on a ``__ID:`` marker embedded in the excerpt.
# ---------------------------------------------------------------------------
class MockLLM:
    def __init__(self, score_map: Dict[str, Dict]):
        self.score_map = score_map

    async def generate_json(self, model_name: str, prompt: str, temperature: float = 0.2):
        # The ``score_commercial_node`` inserts the first 3000 chars of ``source_content``
        # into the prompt. Our mock excerpts contain a marker ``__ID:X__``.
        marker = next((line for line in prompt.split('\n') if line.startswith('__ID:')), None)
        if marker:
            ep_id = marker.split(':', 1)[1].strip('_')
            data = self.score_map.get(ep_id, {"commercial_score": 0.5, "breakdown": {}, "advice": []})
        else:
            data = {"commercial_score": 0.5, "breakdown": {}, "advice": []}
        return type('Resp', (), {'content': json.dumps(data), 'success': True})


def test_correlation_high():
    # Three synthetic works with decreasing bookmark counts.
    works: List[Dict] = [
        {"work_id": "1", "bookmark": 300, "excerpt": "__ID:A__"},
        {"work_id": "2", "bookmark": 200, "excerpt": "__ID:B__"},
        {"work_id": "3", "bookmark": 100, "excerpt": "__ID:C__"},
    ]

    # Scores that follow the same ordering (A > B > C).
    scores_map = {
        "A": {"commercial_score": 0.9, "breakdown": {}, "advice": []},
        "B": {"commercial_score": 0.6, "breakdown": {}, "advice": []},
        "C": {"commercial_score": 0.3, "breakdown": {}, "advice": []},
    }
    mock_llm = MockLLM(scores_map)
    corr = asyncio.run(compute_correlation(works, llm_provider=mock_llm))
    # With a perfect monotonic relationship, Pearson r should be close to 1.
    assert corr > 0.9, f"Correlation too low: {corr}"
