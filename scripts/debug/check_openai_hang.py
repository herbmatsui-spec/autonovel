"""Direct check of OpenAI rate limit path hang."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from unittest.mock import AsyncMock, MagicMock, patch

from src.core.llm_clients.openai import OpenAIApiClient
from src.backend.engine_utils import AdaptiveCooldown


async def main():
    print("step1: create client")
    cooldown = AdaptiveCooldown(base_sec=2.0, min_sec=1.0, max_sec=60.0)
    client = OpenAIApiClient(cooldown)
    mock_async = MagicMock()
    mock_async.chat.completions.create = AsyncMock(side_effect=ValueError("429 too many requests"))
    print("step2: call generate_json")
    with patch("openai.AsyncOpenAI", return_value=mock_async):
        with patch("config.project_context.ProjectContext.get_setting", side_effect=lambda k, d=None: d):
            try:
                result = await asyncio.wait_for(
                    client.generate_json("gemma-3", "p", max_retries=2), timeout=30
                )
                print("no exception:", result)
            except asyncio.TimeoutError:
                print("TIMEOUT - hang confirmed in generate_json")
            except Exception as e:
                print(type(e).__name__, str(e)[:200])


asyncio.run(main())
