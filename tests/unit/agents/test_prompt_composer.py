import pytest
from src.agents.prompt_composer import PromptComposer

def test_prompt_composer_compose():
    composer = PromptComposer()
    composer.add_section("header", "システム指示")
    composer.add_section("content", "本文プロンプト")
    
    full_prompt = composer.build()
    assert "システム指示" in full_prompt
    assert "本文プロンプト" in full_prompt
