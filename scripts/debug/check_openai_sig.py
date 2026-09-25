"""Print OpenAIApiClient method signatures."""

import inspect
import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from src.core.llm_clients.openai import OpenAIApiClient  # noqa: E402

print("generate_json:", inspect.signature(OpenAIApiClient.generate_json))
print("generate_text:", inspect.signature(OpenAIApiClient.generate_text))
