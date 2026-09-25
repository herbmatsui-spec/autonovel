"""Verify OpenAI rate-limit path does not hang under pytest-asyncio style execution."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import AsyncMock, MagicMock, patch

from src.core.llm_clients.openai import OpenAIApiClient
from src.backend.engine_utils import AdaptiveCooldown


async def main():
    cooldown = AdaptiveCooldown(base_sec=2.0, min_sec=1.0, max_sec=60.0)
    client = OpenAIApiClient(cooldown)
    mock_async = MagicMock()
    mock_async.chat.completions.create = AsyncMock(side_effect=ValueError("429 too many requests"))

    with patch("openai.AsyncOpenAI", return_value=mock_async):
        with patch("config.project_context.ProjectContext.get_setting", side_effect=lambda k, d=None: d):
            try:
                await asyncio.wait_for(client.generate_json("gemma-3", "p", max_retries=2), timeout=30)
                print("NO EXCEPTION (unexpected)")
            except asyncio.TimeoutError:
                print("TIMEOUT -> hang inside generate_json")
            except Exception as e:
                print("OK:", type(e).__name__)


asyncio.run(main())
