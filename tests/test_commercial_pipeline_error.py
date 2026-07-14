"""
tests/test_commercial_pipeline_error.py — CommercialPipeline エラー処理単体テスト
"""
import pytest
import asyncio
from src.backend.workflows.commercial_pipeline import CommercialPipeline, PipelineError
from unittest.mock import patch
from src.services.episode_writer import EpisodeWriter


@patch("src.services.episode_writer.EpisodeWriter.write")
async def test_generate_content_raises_pipeline_error_on_episode_write(mock_write):
    """_generate_content が EpisodeWriter のエラーを PipelineError に変換するか"""
    pipeline = CommercialPipeline()
    dummy_bible = {
        "target_eps": 1,
        "target_word_count_per_episode": 1000,
        "genre": "general",
        "concept": "test",
        "keywords": [],
        "target_platforms": ["kakuyomu"],
    }

    # Configure the mock to raise an exception
    async def failing_write(*args, **kwargs):
        raise RuntimeError("Model API unreachable")

    mock_write.side_effect = failing_write

    try:
        await pipeline._generate_content_async(dummy_bible, [], ["kakuyomu"])
        assert False, "Expected PipelineError was not raised"
    except PipelineError as e:
        assert "Content generation failed" in str(e)


@pytest.mark.asyncio
async def test_step_plan_raises_pipeline_error():
    """_step_plan が PipelineError を正しく送出するかを検証"""
    pipeline = CommercialPipeline()
    invalid_config = {"invalid": "config"}  # キーワードが空の無効設定

    with pytest.raises(PipelineError) as exc_info:
        await pipeline._step_plan_async(invalid_config)

    assert "Bible generation failed" in str(exc_info.value)