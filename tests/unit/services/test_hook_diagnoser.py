from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.hook_diagnoser import HookDiagnoser


@pytest.fixture
def mock_quality_scorer():
    scorer = MagicMock()
    scorer.score_hook_retention = AsyncMock()
    return scorer


@pytest.fixture
def hook_diagnoser(mock_quality_scorer, monkeypatch):
    monkeypatch.setattr("src.services.hook_diagnoser.QualityScorer", lambda: mock_quality_scorer)
    return HookDiagnoser(llm_service=None)


@pytest.mark.asyncio
async def test_diagnose(hook_diagnoser, mock_quality_scorer):
    mock_quality_scorer.score_hook_retention.return_value = 0.8
    chapters = [
        {"ep_num": 1, "title": "Chapter 1", "content": "Some content"},
        {"ep_num": 2, "title": "Chapter 2", "content": "Other content"},
    ]
    results = await hook_diagnoser.diagnose(chapters)
    assert len(results) == 2
    assert results[0]["ep_num"] == 1
    assert results[0]["hook_score"] == 0.8
    assert results[0]["is_weak"] is False  # 0.8 >= 0.7
    assert results[1]["ep_num"] == 2
    assert results[1]["hook_score"] == 0.8
    assert results[1]["is_weak"] is False

    # Test with low score
    mock_quality_scorer.score_hook_retention.return_value = 0.5
    results = await hook_diagnoser.diagnose(chapters)
    assert results[0]["is_weak"] is True
    assert results[1]["is_weak"] is True

    # Test exception handling
    mock_quality_scorer.score_hook_retention.side_effect = Exception("scoring error")
    results = await hook_diagnoser.diagnose(chapters)
    assert results[0]["hook_score"] == 0.0
    assert results[1]["hook_score"] == 0.0
    assert results[0]["is_weak"] is True
    assert results[1]["is_weak"] is True


@pytest.mark.asyncio
async def test_detect_weak_hooks(hook_diagnoser, mock_quality_scorer):
    mock_quality_scorer.score_hook_retention.side_effect = [0.9, 0.5, 0.6]
    chapters = [
        {"ep_num": 1, "title": "C1", "content": "text1"},
        {"ep_num": 2, "title": "C2", "content": "text2"},
        {"ep_num": 3, "title": "C3", "content": "text3"},
    ]
    weak = await hook_diagnoser.detect_weak_hooks(chapters)
    assert len(weak) == 2  # ep2 and ep3
    assert weak[0]["ep_num"] == 2
    assert weak[1]["ep_num"] == 3


@pytest.mark.asyncio
async def test_generate_hook_fix_with_llm(hook_diagnoser):
    mock_llm = MagicMock()
    mock_llm.generate_text = AsyncMock(return_value="固定されたフック")
    hook_diagnoser._llm = mock_llm
    chapter = {"content": "本文の内容"}
    result = await hook_diagnoser.generate_hook_fix(chapter, api_key="dummy")
    assert result == "固定されたフック"
    mock_llm.generate_text.assert_awaited_once()
    args, kwargs = mock_llm.generate_text.call_args
    assert kwargs["purpose"] == "writing"
    assert "章末の書き換え案" in kwargs["prompt"]
    assert "本文の内容" in kwargs["prompt"]


@pytest.mark.asyncio
async def test_generate_hook_fix_without_llm(hook_diagnoser, monkeypatch):
    mock_llm_instance = MagicMock()
    mock_llm_instance.generate_text = AsyncMock(return_value="自動生成フック")
    monkeypatch.setattr("src.services.llm_service.LLMService", lambda api_key: mock_llm_instance)

    hook_diagnoser._llm = None
    chapter = {"content": "本文"}
    result = await hook_diagnoser.generate_hook_fix(chapter, api_key="dummy")
    assert result == "自動生成フック"


@pytest.mark.asyncio
async def test_generate_hook_fix_exception(hook_diagnoser):
    mock_llm = MagicMock()
    mock_llm.generate_text = AsyncMock(side_effect=RuntimeError("LLM failed"))
    hook_diagnoser._llm = mock_llm
    chapter = {"content": "本文"}
    result = await hook_diagnoser.generate_hook_fix(chapter, api_key="dummy")
    assert result == ""
