"""General scene continuity: persistence, detection and transition contracts."""
import sqlite3

import pytest
from pydantic import ValidationError

from src.agents.erotic.continuity import SceneContinuityTracker, SceneStateSnapshot


@pytest.fixture
def tracker(tmp_path):
    return SceneContinuityTracker(str(tmp_path / "scenes.db"))


def test_snapshot_defaults_are_independent():
    first = SceneStateSnapshot()
    second = SceneStateSnapshot()
    first.discoveries.append("map")
    first.items_held.append("key")
    assert second.discoveries == []
    assert second.items_held == []
    with pytest.raises(ValidationError):
        SceneStateSnapshot(unexpected=True)


@pytest.mark.parametrize("attitude,tag", [
    ("neutral", None), ("hostile", "glaring, tense atmosphere"),
    ("friendly", "gentle smile, warm lighting"),
])
def test_illustration_tags(attitude, tag):
    snapshot = SceneStateSnapshot(character_name="Aki", scene_type="exploration",
                                  time_of_day="morning", attitude=attitude,
                                  injury_level="light")
    prompt = snapshot.to_illustration_prompt(["forest"])
    for expected in ["Aki", "exploration scene", "morning", "scratches", "forest", "masterpiece"]:
        assert expected in prompt
    if tag:
        assert tag in prompt
    assert "unknown" not in SceneStateSnapshot().to_illustration_prompt()


def test_persistence_replacement_and_character_isolation(tracker):
    snapshot = SceneStateSnapshot(character_name="Aki", episode_num=1,
                                  discoveries=["秘密を発見した"], items_held=["鍵"],
                                  foreshadowing_active=True, time_of_day="night")
    tracker.save_snapshot(snapshot)
    reopened = SceneContinuityTracker(tracker.db_path)
    assert reopened.get_snapshot(1, "Aki") == snapshot
    assert reopened.get_previous_snapshot(2, "Aki") == snapshot
    assert reopened.get_snapshot(1, "Other") is None
    assert reopened.get_previous_snapshot(3, "Aki") is None
    snapshot.items_held = ["盾"]
    reopened.save_snapshot(snapshot)
    assert tracker.get_snapshot(1, "Aki").items_held == ["盾"]
    with sqlite3.connect(tracker.db_path) as conn:
        assert conn.execute("SELECT count(*) FROM scene_snapshots").fetchone()[0] == 1
        conn.execute("UPDATE scene_snapshots SET discoveries=NULL, items_held=NULL")
    restored = tracker.get_snapshot(1, "Aki")
    assert restored.discoveries == []
    assert restored.items_held == []


@pytest.mark.parametrize("method,text,expected", [
    ("_detect_injury_level", "", "none"),
    ("_detect_injury_level", "かすり傷", "light"),
    ("_detect_injury_level", "骨折", "moderate"),
    ("_detect_injury_level", "瀕死で骨折とかすり傷", "severe"),
    ("_detect_attitude", "", "neutral"),
    ("_detect_attitude", "拒絶", "hostile"),
    ("_detect_attitude", "警戒", "tense"),
    ("_detect_attitude", "信頼", "friendly"),
    ("_detect_discoveries", "歩く。 秘密を発見した。鍵を見つけた。", ["秘密を発見した", "鍵を見つけた"]),
    ("_detect_discoveries", "。 ", []),
    ("_detect_travel_state", "出発して到着", "departing"),
    ("_detect_travel_state", "到着", "arriving"),
    ("_detect_travel_state", "待つ", "staying"),
    ("_detect_monologue_perspective", "私は待つ", "first_person"),
    ("_detect_monologue_perspective", "彼が待つ", "third_person"),
    ("_detect_perspective", "私が待つ", "first_person"),
    ("_detect_perspective", "彼が待つ", "third_person"),
    ("_detect_recovery_state", "休息して回復", "resting"),
    ("_detect_recovery_state", "回復", "recovering"),
    ("_detect_recovery_state", "戦闘", "action"),
    ("_detect_recovery_state", "剣を振る", "action"),
    ("_detect_recovery_state", "待つ", "unknown"),
    ("_detect_time_of_day", "朝日", "morning"),
    ("_detect_time_of_day", "正午", "day"),
    ("_detect_time_of_day", "夕暮れ", "evening"),
    ("_detect_time_of_day", "月明かり", "night"),
    ("_detect_time_of_day", "待つ", "unknown"),
])
def test_detection_contracts(tracker, method, text, expected):
    assert getattr(tracker, method)(text) == expected


@pytest.mark.parametrize("method,previous,text,warning", [
    ("injury", {"injury_level": "severe"}, "歩く", "整合性警告"),
    ("injury", {"injury_level": "severe"}, "治療して歩く", None),
    ("injury", {}, "骨折", "状態急変"),
    ("injury", {}, "かすり傷", None),
    ("attitude", {"attitude": "hostile"}, "信頼", "整合性警告"),
    ("attitude", {"attitude": "hostile"}, "拒絶", None),
    ("attitude", {"attitude": "hostile"}, "歩く", None),
    ("attitude", {}, "信頼", None),
    ("discovery", {"discoveries": ["秘密を発見した"]}, "歩く", "一貫性警告"),
    ("discovery", {"discoveries": ["秘密を発見した"]}, "秘密を発見した。", None),
    ("discovery", {"discoveries": ["石を見つけた"]}, "歩く", None),
    ("travel", {"travel_state": "departing"}, "歩く", "移動断絶"),
    ("travel", {"travel_state": "departing"}, "到着", None),
    ("travel", {"travel_state": "arriving"}, "出発", "移動断絶"),
    ("travel", {"travel_state": "arriving"}, "宿屋から出発", None),
    ("travel", {}, "歩く", None),
    ("perspective", {"perspective": "first_person"}, "彼が歩く", "視点警告"),
    ("perspective", {"perspective": "first_person"}, "私は歩く", None),
    ("perspective", {"perspective": ""}, "彼が歩く", None),
    ("recovery", {"recovery_state": "action", "injury_level": "severe"}, "回復", "一貫性警告"),
    ("recovery", {"recovery_state": "action", "injury_level": "moderate"}, "薬で回復", None),
    ("recovery", {"recovery_state": "action", "injury_level": "moderate"}, "戦闘", "連戦警告"),
    ("recovery", {"recovery_state": "action", "injury_level": "moderate"}, "待つ", None),
    ("recovery", {"recovery_state": "action"}, "戦闘", None),
    ("recovery", {"recovery_state": "resting"}, "戦闘", "整合性警告"),
    ("recovery", {"recovery_state": "exhausted"}, "元気に戦闘", None),
    ("foreshadowing", {"foreshadowing_active": True}, "歩く", "伏線警告"),
    ("foreshadowing", {"foreshadowing_active": True}, "解決", None),
    ("foreshadowing", {}, "歩く", None),
    ("time", {"time_of_day": "morning"}, "月明かり", "時間帯"),
    ("time", {"time_of_day": "morning"}, "数時間後の月明かり", None),
    ("time", {"time_of_day": "morning"}, "正午", None),
    ("time", {"time_of_day": "morning"}, "朝日", None),
    ("time", {"time_of_day": "morning"}, "歩く", None),
    ("time", {}, "月明かり", None),
    ("item", {"items_held": ["鍵"]}, "歩く", "消失"),
    ("item", {"items_held": ["鍵"]}, "鍵を持つ", None),
    ("item", {"items_held": ["鍵"]}, "捨てる", None),
    ("item", {}, "歩く", None),
])
def test_continuity_transitions(tracker, method, previous, text, warning):
    tracker.save_snapshot(SceneStateSnapshot(character_name="Aki", episode_num=1, **previous))
    issues = getattr(tracker, f"check_{method}_continuity")(2, "Aki", text)
    if warning:
        assert len(issues) == 1
        assert warning in issues[0]
    else:
        assert issues == []


def test_all_checks_without_history(tracker):
    assert tracker.check_all_continuity(1, "Aki", "私は朝に出発した。") == []


def test_all_checks_aggregate_real_warnings(tracker):
    tracker.save_snapshot(SceneStateSnapshot(character_name="Aki", episode_num=1,
                                            injury_level="severe", items_held=["鍵"],
                                            perspective="third_person"))
    issues = tracker.check_all_continuity(2, "Aki", "彼が歩く。")
    assert len(issues) == 2
    assert "負傷状態" in issues[0]
    assert "消失" in issues[1]


def test_extract_snapshot_composes_detectors(tracker):
    snapshot = tracker.extract_snapshot("私は朝に出発した。かすり傷を負い、信頼する仲間と休息する。鍵を見つけた。")
    assert snapshot.injury_level == "light"
    assert snapshot.attitude == "friendly"
    assert snapshot.travel_state == "departing"
    assert snapshot.recovery_state == "resting"
    assert snapshot.perspective == "first_person"
    assert snapshot.time_of_day == "morning"
    assert snapshot.discoveries == ["鍵を見つけた"]
    assert "鍵" in snapshot.items_held
