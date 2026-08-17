import pytest
from src.easy_mode.bible_generator import BibleGenerator
from src.easy_mode.models import RetryConfig

@pytest.mark.asyncio
async def test_bible_generator_generate():
    # Mock dependencies
    preset = {"bible": "テストテンプレート"}
    class MockLLM:
        async def generate(self, *args, **kwargs):
            return '{"world_rules_json": "test", "concept": "test"}'
    engine_llm = MockLLM()
    retry_config = RetryConfig()

    generator = BibleGenerator(preset, engine_llm, retry_config)
    result = await generator.generate(target_episodes=1)
    assert isinstance(result, dict)
    # At least check that some expected keys are present
    assert "world_rules_json" in result
    assert "concept" in result
    assert result["world_rules_json"] == "test"
    assert result["concept"] == "test"
