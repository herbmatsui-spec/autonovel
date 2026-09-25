"""Inspect retry_decorator source around LLMTemporaryError handling."""

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import io

import src.services.retry_decorator as rd

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

inner = rd.with_llm_retry()
src = inspect.getsource(inner)
idx = src.find("LLMTemporaryError")
while idx != -1:
    print("---")
    chunk = src[max(0, idx - 400): idx + 150]
    print(chunk.encode("utf-8", errors="replace").decode("utf-8", errors="replace"))
    idx = src.find("LLMTemporaryError", idx + 1)
