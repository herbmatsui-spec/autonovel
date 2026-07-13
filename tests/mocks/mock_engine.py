import logging
from unittest.mock import AsyncMock

from src.models import GenerateResult

logger = logging.getLogger(__name__)

class MockEngine:
    """Mock Engine simulating UltimateHegemonyEngine for integration tests."""
    def __init__(self, mock_llm=None):
        self.mock_llm = mock_llm
        self.repo = AsyncMock()
        self.pm = AsyncMock()
        self.ctx_mgr = AsyncMock()
        self.ctx_mgr.get_optimal_context = AsyncMock(return_value=("char_ctx", "prev_ctx"))

        self.logic_validator = AsyncMock()
        self.auditor = AsyncMock()
        self.narrative = AsyncMock()

        if mock_llm:
            self.generate_text = mock_llm.generate_text
        else:
            self.generate_text = AsyncMock(return_value=("Mock story content.", None))

    async def generate_json(self, *args, **kwargs):
        if self.mock_llm:
            res, _, _ = await self.mock_llm.generate_json(*args, **kwargs)
            return GenerateResult(success=True, metadata=res, story_content="")
        return GenerateResult(success=True, metadata={"status": "success"}, story_content="")
