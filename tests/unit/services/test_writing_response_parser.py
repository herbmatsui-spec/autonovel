import pytest
import re

def clean_writing_response(text: str) -> str:
    cleaned = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL)
    return cleaned.strip()

def test_clean_writing_response_strip_thinking():
    raw = "<thinking>プロットの整理...</thinking>「こんにちは」と彼女は言った。"
    cleaned = clean_writing_response(raw)
    assert "<thinking>" not in cleaned
    assert "「こんにちは」" in cleaned
