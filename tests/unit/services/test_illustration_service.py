import pytest
from src.services.illustration.prompt_builder import PromptBuilder

def test_generate_prompt_from_scene():
    prompt = PromptBuilder.build_positive_prompt(
        base_prompt="silver hair girl, blue dress",
        character_additions="bright eyes",
        quality_enhancement=True
    )
    assert "silver hair girl" in prompt
    assert "masterpiece" in prompt

def test_build_negative_prompt():
    neg = PromptBuilder.build_negative_prompt(custom_negative="ugly face", include_standard=True)
    assert "bad anatomy" in neg
    assert "ugly face" in neg
