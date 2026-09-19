"""
Unit tests for token dictionary and prompt integration (PLAN_Y3 Step 2, 3).
"""

from pathlib import Path
import pytest
import yaml
from src.narrative.subtext_tokens.expander import TokenExpander
from src.narrative.subtext_tokens.parser import TokenParser


def test_token_dictionary_loading():
    dict_path = Path("data/subtext/tokens.yaml")
    assert dict_path.exists()
    data = yaml.safe_load(dict_path.read_text(encoding="utf-8"))
    assert "subtext" in data
    assert "beat" in data
    assert "irony" in data.get("subtext", {})


def test_prompt_template_has_subtext_instructions():
    prompt_path = Path("prompts/templates/narrative/dialogue_generation.j2")
    assert prompt_path.exists()
    content = prompt_path.read_text(encoding="utf-8")
    assert "[SUBTEXT:irony]" in content
    assert "[BEAT:pause" in content
    assert "[ACTION:hide_hands" in content
