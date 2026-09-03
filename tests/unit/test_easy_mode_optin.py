import pytest
from unittest.mock import AsyncMock, MagicMock
from src.domain.entities.easy_mode import EasyModeInput, LLMConfigOverride
from src.services.llm.factory import get_llm_adapter
from src.services.llm.gemini_adapter import GeminiAdapter
from src.services.llm.mock_adapter import MockLLMAdapter
from src.services.llm.openai_adapter import OpenAIAdapter
from src.backend.workflows.reverse_plot_workflow import ReversePlotGenerationWorkflow


def test_llm_factory_optin_gemini():
    # Per-request Gemini API key should instantiate GeminiAdapter
    adapter = get_llm_adapter(
        provider="gemini",
        api_key="AIzaSyTestKey123",
        model_name="gemini-2.5-pro",
    )
    assert isinstance(adapter, GeminiAdapter)
    assert adapter.api_key == "AIzaSyTestKey123"
    assert adapter.model_name == "gemini-2.5-pro"


def test_llm_factory_optin_openai():
    # Per-request OpenAI API key and custom base_url
    adapter = get_llm_adapter(
        provider="openai",
        api_key="sk-test-key-456",
        model_name="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
    )
    assert isinstance(adapter, OpenAIAdapter)
    assert adapter.api_key == "sk-test-key-456"
    assert adapter.model == "deepseek-chat"
    assert adapter.base_url == "https://api.deepseek.com/v1"


def test_llm_factory_fallback_to_mock():
    # No key provided and no env key should fallback to MockLLMAdapter safely
    adapter = get_llm_adapter(provider="mock")
    assert isinstance(adapter, MockLLMAdapter)


def test_easy_mode_input_with_50_episodes_and_optin_llm():
    inp = EasyModeInput(
        current_chapter="冒険の始まり",
        content_length_limit=4000,
        target_episodes=50,
        llm_config=LLMConfigOverride(
            provider="gemini",
            api_key="AIzaSyDummyKey",
            model_name="gemini-2.5-flash",
        ),
    )
    assert inp.content_length_limit == 4000
    assert inp.target_episodes == 50
    assert inp.llm_config is not None
    assert inp.llm_config.provider == "gemini"
    assert inp.llm_config.api_key == "AIzaSyDummyKey"


@pytest.mark.asyncio
async def test_reverse_plot_workflow_50_episodes():
    workflow = ReversePlotGenerationWorkflow()
    answers = {
        "emotionalGoal": "triumph",
        "sacrifice": "peace",
        "coreConflict": "ideal_vs_reality",
        "openingHook": "isekai_awakening",
    }
    result = await workflow.execute(answers=answers, target_episodes=50, genre="ハイファンタジー (R15)")

    assert len(result["episodes"]) == 50
    assert result["episodes"][0]["ep_num"] == 1
    assert result["episodes"][49]["ep_num"] == 50
    assert len(result["arcs"]) == 3
    assert result["arcs"][0]["start_ep"] == 1
    assert result["arcs"][-1]["end_ep"] == 50
    assert len(result["catharsis_pattern"]["tension_wave"]) == 50


@pytest.mark.asyncio
async def test_streaming_generator_with_optin_config():
    from src.backend.routers.streaming import _stream_generator
    from src.domain.entities.easy_mode import CharacterParams

    inp = EasyModeInput(
        chapter_history=["前回のあらすじ"],
        current_chapter="ダンジョン深層へ進む",
        character_params=CharacterParams(
            name="テスト主人公",
            personality="冷静沈着",
            ability="影魔法",
            genre="ハイファンタジー (R15)",
        ),
        content_length_limit=3000,
        target_episodes=10,
        llm_config=LLMConfigOverride(
            provider="mock",
        ),
    )

    # モック Request オブジェクトを作成（is_disconnected は常に False を返す）
    mock_request = MagicMock()
    mock_request.is_disconnected = AsyncMock(return_value=False)

    events = []
    async for item in _stream_generator(inp, mock_request):
        events.append(item)

    assert len(events) >= 2
    assert "data: " in events[0]
    assert '"type": "start"' in events[0]
    assert any('"type": "done"' in e for e in events)

