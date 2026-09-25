"""Check whether generate_json accepts nsfw_mode."""

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import inspect  # noqa: E402

from src.core.llm_clients import openai as oa  # noqa: E402

sig = inspect.signature(oa.OpenAIApiClient.generate_json)
print("params:", list(sig.parameters.keys()))
print("nsfw_mode in generate_json:", "nsfw_mode" in sig.parameters)
