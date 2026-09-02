"""EditorAssistService の単体テスト."""
from unittest.mock import AsyncMock, MagicMock
import pytest

from src.models.editor import (
    AssistAction,
    AssistRequest,
    SensoryType,
    ToneType,
)
from src.services.editor_assist_service import EditorAssistService


@pytest.fixture
def mock_llm_gateway():
    mock = MagicMock()
    mock_result = MagicMock()
    mock_result.story_content = "重厚な鉄の扉が、軋んだ甲高い悲鳴を上げながらゆっくりと開かれた。"
    mock_result.content = mock_result.story_content
    mock_result.success = True
    mock.generate_text = AsyncMock(return_value=mock_result)
    return mock


@pytest.mark.asyncio
async def test_expand_sensory(mock_llm_gateway):
    """五感拡張のテスト"""
    service = EditorAssistService(llm_gateway=mock_llm_gateway)
    res = await service.expand_sensory(
        text="男は扉を開けた。",
        sensory_type=SensoryType.AUDITORY,
        genre="ダークファンタジー (R15)",
        context_before="背後から敵の足音が迫る中、",
    )
    assert "軋んだ甲高い悲鳴" in res
    assert mock_llm_gateway.generate_text.called


@pytest.mark.asyncio
async def test_show_dont_tell(mock_llm_gateway):
    """Show, Don't Tell 変換のテスト"""
    service = EditorAssistService(llm_gateway=mock_llm_gateway)
    res = await service.show_dont_tell(
        text="アリスは悲しかった。",
        genre="ハイファンタジー (R15)",
    )
    assert res is not None
    assert mock_llm_gateway.generate_text.called


@pytest.mark.asyncio
async def test_rewrite_tone(mock_llm_gateway):
    """トーン変換のテスト"""
    service = EditorAssistService(llm_gateway=mock_llm_gateway)
    res = await service.rewrite_tone(
        text="アルトは剣を抜いた。",
        tone_type=ToneType.TENSION,
    )
    assert res is not None
    assert mock_llm_gateway.generate_text.called


@pytest.mark.asyncio
async def test_assist_dispatcher(mock_llm_gateway):
    """assist メソッドのディスパッチテスト"""
    service = EditorAssistService(llm_gateway=mock_llm_gateway)
    req = AssistRequest(
        text="男は扉を開けた。",
        action=AssistAction.DESCRIBE,
        sensory_type=SensoryType.VISUAL,
    )
    res = await service.assist(req)
    assert res.action == AssistAction.DESCRIBE
    assert res.original_text == "男は扉を開けた。"
    assert "五感描写（visual）を拡張" in res.diff_summary
    assert res.result_text == "重厚な鉄の扉が、軋んだ甲高い悲鳴を上げながらゆっくりと開かれた。"
