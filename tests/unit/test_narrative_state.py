"""
tests/unit/test_narrative_state.py - Phase 1: NarrativeState ハブの単体テスト
"""

import pytest
from src.backend.workflows.narrative_state import NarrativeState
from src.backend.workflows.state import MasterGraphState


def test_narrative_state_defaults():
    """ステップ 1: デフォルト値の確認"""
    hub = NarrativeState()
    assert hub.book_id == 1
    assert hub.branch_id == 1
    assert hub.episodes == {}
    assert hub.tension_curve == []
    assert hub.affinity_map == {}
    assert hub.foreshadow_registry == []
    assert hub.continuity_violations == []
    assert hub.quality_scores == {}
    assert hub.erotic_metrics == {}
    assert hub.narrative_scores == {}


def test_narrative_state_upsert_episode():
    """ステップ 3: upsert_episode ヘルパーの確認"""
    hub = NarrativeState()
    hub.upsert_episode(1, char_count=300)
    assert hub.episodes[1]["char_count"] == 300

    # 追記更新
    hub.upsert_episode(1, tension=0.85)
    assert hub.episodes[1]["char_count"] == 300
    assert hub.episodes[1]["tension"] == 0.85


def test_narrative_state_serialization_roundtrip():
    """ステップ 2 & 4: to_dict / from_dict ラウンドトリップ"""
    hub = NarrativeState(book_id=42, branch_id=2)
    hub.upsert_episode(1, text="Hello", quality={"score": 90})
    hub.tension_curve.append(0.75)
    hub.affinity_map["メインヒロイン"] = 80.0
    hub.continuity_violations.append({"field": "hp", "msg": "jumped"})
    hub.quality_scores[1] = {"score": 90}
    hub.erotic_metrics[1] = {"intensity": 50}
    hub.narrative_scores[1] = {"audit": "pass"}

    d = hub.to_dict()
    assert isinstance(d, dict)
    assert d["book_id"] == 42
    assert d["branch_id"] == 2
    assert d["episodes"][1]["text"] == "Hello"
    assert d["tension_curve"] == [0.75]
    assert d["affinity_map"]["メインヒロイン"] == 80.0
    assert len(d["continuity_violations"]) == 1

    restored = NarrativeState.from_dict(d)
    assert restored.book_id == 42
    assert restored.branch_id == 2
    assert restored.episodes[1]["text"] == "Hello"
    assert restored.tension_curve == [0.75]
    assert restored.affinity_map["メインヒロイン"] == 80.0
    assert restored.continuity_violations == [{"field": "hp", "msg": "jumped"}]
    assert restored.quality_scores[1] == {"score": 90}
    assert restored.erotic_metrics[1] == {"intensity": 50}
    assert restored.narrative_scores[1] == {"audit": "pass"}

    # AffinityData オブジェクトでのラウンドトリップ
    from src.schemas.ux_schemas import AffinityData
    hub_with_obj = NarrativeState()
    hub_with_obj.affinity_map["ヒロイン"] = AffinityData(
        character_name="ヒロイン",
        affinity_score=85.0,
        trust_score=70.0,
        wariness_score=15.0,
        current_mood="affectionate"
    )
    d2 = hub_with_obj.to_dict()
    assert isinstance(d2["affinity_map"]["ヒロイン"], dict)
    assert d2["affinity_map"]["ヒロイン"]["trust_score"] == 70.0

    restored2 = NarrativeState.from_dict(d2)
    assert isinstance(restored2.affinity_map["ヒロイン"], AffinityData)
    assert restored2.affinity_map["ヒロイン"].current_mood == "affectionate"


def test_master_graph_state_with_narrative_hub():
    """ステップ 5 & 6: MasterGraphState が narrative ハブを保持できること"""
    hub = NarrativeState(book_id=10, branch_id=3)
    state: MasterGraphState = {
        "task_id": "test_task",
        "narrative": hub,
    }
    assert state.get("narrative") is hub
    assert state["narrative"].book_id == 10
