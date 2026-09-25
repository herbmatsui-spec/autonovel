"""Check Gemini fast_executor approach works."""

import asyncio
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from unittest.mock import MagicMock

from src.core import executor_manager as em


async def _run_io(func, *a, **k):
    return func(*a, **k)


em.executor_manager.run_io = _run_io

from src.core.llm_clients.gemini import GeminiApiClient  # noqa: E402
from src.backend.engine_utils import AdaptiveCooldown  # noqa: E402

resp = MagicMock()
resp.text = '{"title": "T", "score": 5}'
resp.usage_metadata = None
mock_client = MagicMock()
mock_client.models.generate_content.return_value = resp
client = GeminiApiClient(mock_client, AdaptiveCooldown(base_sec=2.0, min_sec=1.0, max_sec=60.0))
m, s, u = asyncio.run(client.generate_json("gemini-pro", "p"))
print("OK", m)
