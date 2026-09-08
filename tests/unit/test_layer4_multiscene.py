"""Unit tests for Layer 4 Multi-scene awareness and Protected Token pinning (Part 5 / Steps 49-54)."""

import pytest

from src.services.compression.layer4_trimming import (
    Layer4SceneTrimmer,
    Layer4DynamicTrimmer,
    SCENE_CATEGORY_WEIGHTS,
    SCENE_KEYWORDS_WEIGHTED,
)
from src.services.compression.models import (
    AbstractionLayerOutput,
    ProtectedContext,
    SceneType,
)


def test_9_scene_types_weights_and_keywords():
    """Test completeness of 9-scene types weights matrix and keyword dictionaries (Steps 49-51)."""
    expected_scenes = [
        "combat", "daily", "psychological", "political",
        "romance", "mystery", "flashback", "survival", "general",
    ]

    for sc in expected_scenes:
        assert sc in SCENE_CATEGORY_WEIGHTS
        weights = SCENE_CATEGORY_WEIGHTS[sc]
        assert len(weights) >= 5
        assert all(w > 0 for w in weights.values())

    # Keywords for new scene types
    for sc in ["romance", "mystery", "flashback", "survival"]:
        assert sc in SCENE_KEYWORDS_WEIGHTED
        assert len(SCENE_KEYWORDS_WEIGHTED[sc]) >= 5


def test_scene_detection_multilabel():
    """Test detecting new scene types from keywords (Step 51)."""
    trimmer = Layer4SceneTrimmer()

    # Romance scene
    romance_text = "二人は夕暮れの海辺でデートし、照れながら視線を交わして愛を告白した。"
    detected_romance = trimmer.detect_scene_type(romance_text)
    assert detected_romance == "romance"

    # Mystery scene
    mystery_text = "密室の洋館で発見された凶器の遺留品と、完璧なアリバイを持つ犯人の矛盾。"
    detected_mystery = trimmer.detect_scene_type(mystery_text)
    assert detected_mystery == "mystery"

    # Flashback scene
    flashback_text = "かつて幼少のあの頃、失われた遠い過去の記憶と面影を追憶する。"
    detected_flashback = trimmer.detect_scene_type(flashback_text)
    assert detected_flashback == "flashback"


def test_protected_context_attention_pinning():
    """Test that active characters and pending foreshadowings are pinned (Steps 52-53)."""
    trimmer = Layer4SceneTrimmer(max_tokens=300)

    abstraction = AbstractionLayerOutput(
        abstract_concepts=["近接剣術スキル", "古代遺物"],
        categorized_facts={
            "主要キャラ": [
                {"entity": "アリス", "fact": "アリスは王国の元筆頭魔術師。"},
                {"entity": "ボブ", "fact": "ボブは遠くの離宮で静養している。"},
                {"entity": "キャロル", "fact": "キャロルは酒場の用心棒。"},
            ],
            "伏線": [
                {"entity": "FS-001", "fact": "FS-001: 滅びの黒幕の予言が残されている。"},
                {"entity": "FS-002", "fact": "FS-002: 次代の継承者に関する噂。"},
            ],
            "核心設定": [
                {"entity": "魔力炉", "fact": "魔力炉の暴走危険性。"},
            ],
        },
    )

    # Active in this scene: "アリス", Pending foreshadowing: "FS-001"
    protected = ProtectedContext(
        active_characters=["アリス"],
        pending_foreshadowing_ids=["FS-001"],
    )

    trimmed = trimmer.trim(
        abstraction_output=abstraction,
        scene_type="general",
        max_tokens=200,
        protected_context=protected,
    )

    # Pinned entities must be strictly retained in final text
    assert "アリス" in trimmed.retained_entities
    assert "FS-001" in trimmed.retained_entities
    assert "【現在同席】" in trimmed.compressed_text
    assert "【最重要伏線】" in trimmed.compressed_text
