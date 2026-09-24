"""Unit tests for emotion detection prompt."""
from pathlib import Path


def test_prompt_contains_rules():
    prompt_file = Path("src/agents/prompts/emotion_detection.md")
    assert prompt_file.exists()
    content = prompt_file.read_text(encoding="utf-8")

    assert "update_emotion" in content
    assert "delta" in content
    assert "recall_similar_scene" in content
