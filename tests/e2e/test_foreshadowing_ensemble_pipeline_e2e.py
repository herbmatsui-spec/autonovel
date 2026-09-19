"""End-to-End Pipeline test for the zero-LLM ensemble foreshadowing resolution system."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass

from src.agents.orchestrator import AgentContext
from src.agents.writing.episode_writer import EpisodeWriter
from src.services.foreshadowing_service import ForeshadowingService


@dataclass
class ForeshadowingItem:
    id: int
    book_id: int
    title: str
    target_episode: int
    status: str = "planted"
    keywords: list[str] = None

    def __post_init__(self):
        if self.keywords is None:
            self.keywords = []


@pytest.mark.asyncio
async def test_full_foreshadowing_ensemble_pipeline():
    """E2E flow: prompt -> writing -> split -> zero-LLM ensemble -> DB update."""

    # 1. Setup Mock DB repository with an unresolved foreshadowing
    mock_repo = MagicMock()
    mock_repo.get_unresolved = AsyncMock(
        return_value=[
            ForeshadowingItem(
                id=77,
                book_id=1,
                title="聖剣の封印",
                target_episode=10,
                keywords=["聖剣", "封印"],
            )
        ]
    )
    mock_repo.resolve = AsyncMock(return_value=True)

    # 2. Simulate LLM generating prose with co-generated [METADATA_JSON]
    raw_generation = (
        "第10話 クライマックス決戦。\n"
        "少年は剣身に触れ、祈りを捧げた。その瞬間、眩い光とともに聖剣の封印が解けた。\n"
        "周囲の闇は一瞬にして消え去った。\n\n"
        "[METADATA_JSON]\n"
        "{\n"
        '  "episode_number": 10,\n'
        '  "foreshadowings": [\n'
        "    {\n"
        '      "foreshadowing_id": 77,\n'
        '      "action": "resolved",\n'
        '      "rationale": "聖剣の封印が解けた",\n'
        '      "excerpt": "聖剣の封印が解けた"\n'
        "    }\n"
        "  ],\n"
        '  "word_count_estimate": 1500,\n'
        '  "unresolved_notes": []\n'
        "}\n"
        "[/METADATA_JSON]"
    )

    llm_mock = MagicMock()
    llm_mock.generate_text = AsyncMock(return_value=raw_generation)

    prompt_manager_mock = MagicMock()
    prompt_manager_mock.build_final_writing_prompt = AsyncMock(return_value="[writing prompt]")

    context_builder_mock = MagicMock()

    # 3. Instantiate EpisodeWriter
    writer = EpisodeWriter(
        llm=llm_mock,
        context_builder=context_builder_mock,
        prompt_manager=prompt_manager_mock,
    )

    # 4. Execute writing agent run
    ctx = AgentContext(
        book_id=1,
        branch_id=1,
        ep_num=10,
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

    written_text = result.artifacts["written_text"]
    writing_metadata = result.artifacts["writing_metadata"]

    # Verify output prose cleanliness
    assert "[METADATA_JSON]" not in written_text
    assert "聖剣の封印が解けた" in written_text
    assert writing_metadata is not None
    assert len(writing_metadata.foreshadowings) == 1

    # 5. Execute ForeshadowingService check_and_resolve with ensemble
    foreshadowing_service = ForeshadowingService(mock_repo)
    resolved_titles = await foreshadowing_service.check_and_resolve(
        book_id=1,
        episode_num=10,
        draft_text=written_text,
        writing_metadata=writing_metadata,
        contract_ids=[77],
    )

    # 6. Verify assertions
    assert "聖剣の封印" in resolved_titles
    mock_repo.resolve.assert_awaited_once_with(77, 10)

    # CRITICAL: Verify ZERO extra LLM calls were made during post-resolution evaluation
    # (The only LLM call was the single writing generation in step 4)
    assert llm_mock.generate_text.call_count == 1
