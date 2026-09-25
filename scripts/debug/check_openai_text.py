"""Inspect OpenAIApiClient.generate_text source."""

import inspect
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.core.llm_clients import openai as oa  # noqa: E402

print(inspect.getsource(oa.OpenAIApiClient.generate_text))
