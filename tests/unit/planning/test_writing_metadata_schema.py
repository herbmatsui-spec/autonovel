"""Unit tests for WritingMetadata and ForeshadowingReport schemas."""

import pytest
from pydantic import ValidationError
from src.models.writing_metadata import WritingMetadata, ForeshadowingReport


def test_valid_writing_metadata_instantiation():
    """Test standard instantiation of WritingMetadata with valid reports."""
    report = ForeshadowingReport(
        foreshadowing_id=42,
        action="resolved",
        rationale="The hero uncovered the secret letter in the library.",
        excerpt="He picked up the yellowed parchment.",
    )
    metadata = WritingMetadata(
        episode_number=5,
        foreshadowings=[report],
        word_count_estimate=2500,
        unresolved_notes=["The identity of the traitor remains concealed."],
    )

    assert metadata.episode_number == 5
    assert len(metadata.foreshadowings) == 1
    assert metadata.foreshadowings[0].foreshadowing_id == 42
    assert metadata.foreshadowings[0].action == "resolved"
    assert metadata.word_count_estimate == 2500
    assert len(metadata.unresolved_notes) == 1


def test_invalid_action_raises_validation_error():
    """Test that invalid action literal raises ValidationError."""
    with pytest.raises(ValidationError):
        ForeshadowingReport(
            foreshadowing_id=1,
            action="exploded",  # Invalid action
            rationale="Something blew up",
        )


def test_json_deserialization():
    """Test deserializing from raw JSON dict."""
    data = {
        "episode_number": 3,
        "foreshadowings": [
            {
                "foreshadowing_id": 10,
                "action": "progressed",
                "rationale": "Clue discovered",
                "excerpt": "A strange crest on the ring",
            },
            {
                "foreshadowing_id": 11,
                "action": "mentioned_only",
                "rationale": "Casual mention in tavern",
                "excerpt": "I heard rumors about the sword",
            },
        ],
        "word_count_estimate": 3100,
        "unresolved_notes": [],
    }
    metadata = WritingMetadata.model_validate(data)
    assert metadata.episode_number == 3
    assert len(metadata.foreshadowings) == 2
    assert metadata.foreshadowings[0].action == "progressed"
    assert metadata.foreshadowings[1].action == "mentioned_only"
