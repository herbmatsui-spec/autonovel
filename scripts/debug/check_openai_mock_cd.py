"""Check OpenAI rate-limit path with mocked cooldown."""

import asyncio
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from unittest.mock import AsyncMock, MagicMock, patch

from src.core.llm_clients.openai import OpenAIApiClient


async def t():
    cd = MagicMock()
    cd.wait = AsyncMock()
    cd.on_rate_limit = MagicMock()
    cd.on_success = MagicMock()
    cd.on_error = MagicMock()
    client = OpenAIApiClient(cd)
    mock_async = MagicMock()
    mock_async.chat.completions.create = AsyncMock(side_effect=ValueError("429 too many requests"))
    with patch("openai.AsyncOpenAI", return_value=mock_async):
        with patch("config.project_context.ProjectContext.get_setting", side_effect=lambda k, d=None: d):
            try:
                await asyncio.wait_for(client.generate_json("gemma-3", "p", max_retries=2), timeout=15)
                print("NO EXC")
            except Exception as e:
                print("OK", type(e).__name__)


asyncio.run(t())
