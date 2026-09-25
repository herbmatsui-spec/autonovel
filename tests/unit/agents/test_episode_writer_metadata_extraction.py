"""Unit tests for EpisodeWriter metadata extraction and prose cleanliness."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.agents.orchestrator import AgentContext
from src.agents.writing.episode_writer import EpisodeWriter
from src.models.writing_metadata import WritingMetadata


@pytest.mark.asyncio
async def test_episode_writer_extracts_metadata_in_run():
    """Verify that EpisodeWriter.run strips metadata from written_text and puts WritingMetadata into artifacts."""
    llm_mock = MagicMock()
    # Mock LLM returning text with [METADATA_JSON]
    raw_llm_response = (
        "勇者は静かに扉を開いた。\n"
        "奥には古い宝箱が輝いていた。\n\n"
        "[METADATA_JSON]\n"
        "{\n"
        '  "episode_number": 1,\n'
        '  "foreshadowings": [\n'
        "    {\n"
        '      "foreshadowing_id": 5,\n'
        '      "action": "resolved",\n'
        '      "rationale": "宝箱を開けてペンダントを入手",\n'
        '      "excerpt": "古い宝箱が輝いていた"\n'
        "    }\n"
        "  ],\n"
        '  "word_count_estimate": 1200,\n'
        '  "unresolved_notes": []\n'
        "}\n"
        "[/METADATA_JSON]"
    )
    llm_mock.generate_text = AsyncMock(return_value=raw_llm_response)

    context_builder_mock = MagicMock()
    prompt_manager_mock = MagicMock()
    prompt_manager_mock.build_final_writing_prompt = AsyncMock(return_value="dummy writing prompt")
    writer = EpisodeWriter(
        llm=llm_mock,
        context_builder=context_builder_mock,
        prompt_manager=prompt_manager_mock,
    )

    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=1,
        artifacts={
            "writing_context": {
                "use_beat_to_scene": False,  # Test through direct write path
                "genre": "fantasy",
                "prose_refiner_enabled": False,
            }
        },
    )

    result = await writer.run(ctx)

    assert result.error is None
    written_text = result.artifacts.get("written_text")
    writing_metadata = result.artifacts.get("writing_metadata")

    # Verify prose is clean of metadata tags
    assert "勇者は静かに扉を開いた。" in written_text
    assert "奥には古い宝箱が輝いていた。" in written_text
    assert "[METADATA_JSON]" not in written_text

    # Verify metadata is parsed into WritingMetadata
    assert isinstance(writing_metadata, WritingMetadata)
    assert writing_metadata.episode_number == 1
    assert len(writing_metadata.foreshadowings) == 1
    assert writing_metadata.foreshadowings[0].foreshadowing_id == 5
    assert writing_metadata.foreshadowings[0].action == "resolved"


@pytest.mark.asyncio
async def test_episode_writer_fallback_without_metadata():
    """Verify that when LLM returns pure text without metadata, writer still returns text and metadata is None."""
    llm_mock = MagicMock()
    pure_text = "ただの純粋な本文です。タグはありません。"
    llm_mock.generate_text = AsyncMock(return_value=pure_text)

    context_builder_mock = MagicMock()
    prompt_manager_mock = MagicMock()
    prompt_manager_mock.build_final_writing_prompt = AsyncMock(return_value="dummy writing prompt")
    writer = EpisodeWriter(
        llm=llm_mock,
        context_builder=context_builder_mock,
        prompt_manager=prompt_manager_mock,
    )

    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=2,
        artifacts={
            "writing_context": {
                "use_beat_to_scene": False,
                "genre": "fantasy",
                "prose_refiner_enabled": False,
            }
        },
    )

    result = await writer.run(ctx)

    assert result.error is None
    assert result.artifacts.get("written_text") == pure_text
    assert result.artifacts.get("writing_metadata") is None
