"""Diagnose generate_text delegation failure."""

import asyncio
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: E402

from src.core.llm_clients.openai import OpenAIApiClient  # noqa: E402
from src.backend.engine_utils import AdaptiveCooldown  # noqa: E402


def make_cd():
    return AdaptiveCooldown(base_sec=2.0, min_sec=1.0, max_sec=60.0)


async def t():
    response = SimpleNamespace(
        choices=[SimpleNamespace(
            message=SimpleNamespace(content="plain story"),
            usage=SimpleNamespace(prompt_tokens=1, completion_tokens=2),
        )]
    )
    mock_async = MagicMock()
    mock_async.chat.completions.create = AsyncMock(return_value=response)

    with patch("openai.AsyncOpenAI", return_value=mock_async):
        with patch("config.project_context.ProjectContext.get_setting", side_effect=lambda k, d=None: d):
            client = OpenAIApiClient(make_cd())
            try:
                result = await asyncio.wait_for(client.generate_text("gemma-3", "prompt"), timeout=15)
                print("OK", result)
            except asyncio.TimeoutError:
                print("TIMEOUT")
            except Exception as e:
                print("EXC", type(e).__name__, str(e)[:150])


asyncio.run(t())
