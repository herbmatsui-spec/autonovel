"""Character continuity: SQLite persistence, detection and transition contracts."""
import sqlite3

import pytest
from pydantic import ValidationError

from src.agents.erotic.continuity import (
    CharacterStateSnapshot,
    ContinuityReport,
    ContinuityTracker,
)


@pytest.fixture
def tracker(tmp_path):
    return ContinuityTracker(str(tmp_path / "continuity.db"))


def test_character_snapshot_defaults():
    snapshot = CharacterStateSnapshot(character_name="Aki", episode_num=1)
    assert snapshot.stamina_level == "normal"
    assert snapshot.psych_state == "neutral"
    assert snapshot.clothing_state == "fully_dressed"
    assert snapshot.intimacy_level == "acquaintance"
    assert snapshot.location == "unknown"
    assert snapshot.custom_flags == {}
    with pytest.raises(ValidationError):
        CharacterStateSnapshot(character_name="Aki", episode_num=1, unexpected=True)


def test_continuity_report_model():
    report = ContinuityReport(is_consistent=True, issues=[], checked_dimensions=["stamina"],
                              character_name="Aki", episode_num=2)
    assert report.is_consistent is True
    assert report.character_name == "Aki"


def test_persistence_across_instances_and_isolation(tracker):
    snapshot = CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                      stamina_level="exhausted",
                                      psych_state="distressed",
                                      clothing_state="fully_undressed",
                                      intimacy_level="stranger",
                                      location="indoor",
                                      custom_flags={"quest": "active"})
    tracker.save_snapshot(snapshot)

    # Reopened tracker loads from SQLite
    reopened = ContinuityTracker(tracker.db_path)
    loaded = reopened.get_snapshot(1, "Aki")
    assert loaded == snapshot
    assert reopened.get_previous_snapshot(1, "Aki") is None
    assert reopened.get_snapshot(2, "Aki") is None
    assert reopened.get_snapshot(1, "Other") is None

    # Memory cache takes priority over SQLite
    updated = snapshot.model_copy(update={"stamina_level": "normal"})
    reopened.save_snapshot(updated)
    assert reopened.get_snapshot(1, "Aki").stamina_level == "normal"
    # Original tracker's stale memory cache is unaffected until cleared
    assert tracker.get_snapshot(1, "Aki").stamina_level == "exhausted"
    tracker._snapshots.clear()
    assert tracker.get_snapshot(1, "Aki").stamina_level == "normal"

    # Same-episode overwrite keeps a single row (UNIQUE constraint)
    with sqlite3.connect(tracker.db_path) as conn:
        count = conn.execute("SELECT count(*) FROM character_continuity_snapshots").fetchone()[0]
        assert count == 1

    # NULL custom_flags degrade gracefully (clear cache to force SQLite read)
    with sqlite3.connect(tracker.db_path) as conn:
        conn.execute("UPDATE character_continuity_snapshots SET custom_flags=NULL")
        conn.commit()
    tracker._snapshots.clear()
    loaded = tracker.get_snapshot(1, "Aki")
    assert loaded.custom_flags == {}
    assert loaded.stamina_level == "normal"


def test_get_snapshot_db_errors_and_corrupt_flags(tmp_path):
    db_path = str(tmp_path / "corrupt.db")
    tracker = ContinuityTracker(db_path)
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                custom_flags={"a": "b"}))
    # Drop the memory cache entry so reads go through SQLite
    tracker._snapshots.clear()

    import sqlite3 as sqlite3_module

    original_connect = sqlite3_module.connect

    def broken_connect(*args, **kwargs):
        raise RuntimeError("db down")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(sqlite3_module, "connect", broken_connect)
        assert tracker.get_snapshot(1, "Aki") is None
        assert tracker.get_previous_snapshot(2, "Aki") is None

    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE character_continuity_snapshots SET custom_flags='{bad json'")
        conn.commit()

    # Corrupted JSON flags degrade to an empty dict
    assert tracker.get_snapshot(1, "Aki").custom_flags == {}


def test_init_db_failure_falls_back_to_memory(tmp_path):
    import sqlite3 as sqlite3_module

    db_path = str(tmp_path / "fail.db")

    def broken_connect(*args, **kwargs):
        raise RuntimeError("locked")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(sqlite3_module, "connect", broken_connect)
        tracker = ContinuityTracker(db_path)
    assert tracker._snapshots == {}

    # In-memory storage still works after init failure
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1))
    assert tracker.get_snapshot(1, "Aki") is not None
    assert tracker.get_snapshot(2, "Aki") is None


def test_save_snapshot_sqlite_failure_keeps_memory(tmp_path):
    import sqlite3 as sqlite3_module

    def broken_connect(*args, **kwargs):
        raise RuntimeError("locked")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(sqlite3_module, "connect", broken_connect)
        tracker = ContinuityTracker(str(tmp_path / "save_fail.db"))
        tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1))
        assert tracker.get_snapshot(1, "Aki") is not None


def test_extract_snapshot_stamina_and_location(tracker):
    # extract_snapshot analyses only the tail 30% for stamina/psych/location:
    # 34 chars -> tail starts at index 23, so keywords must sit in the final 10 chars
    text = "前半" * 12 + "ぐったりぐったり部屋"
    snapshot = tracker.extract_snapshot("Aki", 1, text)
    assert snapshot.stamina_level == "exhausted"
    assert snapshot.location == "indoor"


def test_extract_snapshot_explicit_clothing_state(tracker):
    snapshot = tracker.extract_snapshot("Aki", 1, "平穏な会話。",
                                        clothing_state="partially_undressed")
    assert snapshot.clothing_state == "partially_undressed"


def test_extract_snapshot_full_undress_detection(tracker):
    text = "脱ぐ脱ぐ脱ぐ着る"
    snapshot = tracker.extract_snapshot("Aki", 1, text)
    assert snapshot.clothing_state == "fully_undressed"


def test_extract_snapshot_partial_undress_detection(tracker):
    # partially_undressed requires undress_count > dress_count
    text = "脱ぐ脱ぐ着る"
    snapshot = tracker.extract_snapshot("Aki", 1, text)
    assert snapshot.clothing_state == "partially_undressed"


def test_extract_snapshot_fully_dressed_default(tracker):
    snapshot = tracker.extract_snapshot("Aki", 1, "着る着る着る")
    assert snapshot.clothing_state == "fully_dressed"


def test_detect_stamina_boundaries():
    assert ContinuityTracker._detect_stamina("") == "normal"
    assert ContinuityTracker._detect_stamina("疲弊疲弊") == "exhausted"
    assert ContinuityTracker._detect_stamina("ぐったり") == "normal"
    assert ContinuityTracker._detect_stamina("動けない") == "normal"
    assert ContinuityTracker._detect_stamina("息が荒い息が荒い") == "tired"
    assert ContinuityTracker._detect_stamina("元気元気") == "energetic"


def test_detect_psych_state_boundaries():
    assert ContinuityTracker._detect_psych_state("") == "neutral"
    assert ContinuityTracker._detect_psych_state("絶望絶望") == "distressed"
    assert ContinuityTracker._detect_psych_state("不安不安") == "anxious"
    assert ContinuityTracker._detect_psych_state("安心安心") == "content"
    assert ContinuityTracker._detect_psych_state("恍惚恍惚") == "euphoric"


def test_detect_location_boundaries():
    assert ContinuityTracker._detect_location("") == "unknown"
    assert ContinuityTracker._detect_location("部屋") == "indoor"
    assert ContinuityTracker._detect_location("森") == "outdoor"


def test_detect_intimacy_boundaries():
    assert ContinuityTracker._detect_intimacy("") == "acquaintance"
    assert ContinuityTracker._detect_intimacy("初対面") == "stranger"
    assert ContinuityTracker._detect_intimacy("信頼") == "close"
    assert ContinuityTracker._detect_intimacy("恋人") == "intimate"
    assert ContinuityTracker._detect_intimacy("運命") == "bonded"


def test_detect_clothing_state_boundaries(tracker):
    assert tracker._detect_clothing_state("着る着る着る") == "fully_dressed"
    assert tracker._detect_clothing_state("脱ぐ着る") == "fully_dressed"
    assert tracker._detect_clothing_state("脱ぐ脱ぐ着る") == "partially_undressed"
    assert tracker._detect_clothing_state("脱ぐ脱ぐ脱ぐ着る") == "fully_undressed"
    assert tracker._detect_clothing_state("脱ぐ脱ぐ着る着る着る") == "fully_dressed"


def test_static_numeric_mappers():
    assert ContinuityTracker._stamina_to_num("exhausted") == 0
    assert ContinuityTracker._stamina_to_num("tired") == 1
    assert ContinuityTracker._stamina_to_num("normal") == 2
    assert ContinuityTracker._stamina_to_num("energetic") == 3
    assert ContinuityTracker._stamina_to_num("bogus") == 2
    assert ContinuityTracker._psych_to_num("distressed") == 0
    assert ContinuityTracker._psych_to_num("anxious") == 1
    assert ContinuityTracker._psych_to_num("neutral") == 2
    assert ContinuityTracker._psych_to_num("content") == 3
    assert ContinuityTracker._psych_to_num("euphoric") == 4
    assert ContinuityTracker._psych_to_num("bogus") == 2
    assert ContinuityTracker._intimacy_to_num("stranger") == 0
    assert ContinuityTracker._intimacy_to_num("acquaintance") == 1
    assert ContinuityTracker._intimacy_to_num("close") == 2
    assert ContinuityTracker._intimacy_to_num("intimate") == 3
    assert ContinuityTracker._intimacy_to_num("bonded") == 4
    assert ContinuityTracker._intimacy_to_num("bogus") == 1


def test_check_stamina_continuity(tracker):
    # No history -> no issues
    assert tracker.check_stamina_continuity(2, "Aki", "元気に歩く。") == []
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                stamina_level="exhausted"))
    # exhausted -> energetic is not allowed
    text = "前半" * 20 + "元気元気"
    issues = tracker.check_stamina_continuity(2, "Aki", text)
    assert len(issues) == 1
    assert "[体力矛盾]" in issues[0]
    # exhausted -> tired is allowed
    text = "前半" * 20 + "息が荒い息が荒い"
    assert tracker.check_stamina_continuity(2, "Aki", text) == []


def test_check_recovery_description(tracker):
    assert tracker.check_recovery_description(2, "Aki", "元気に歩く。") == []
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                stamina_level="exhausted"))
    # Recovered without any recovery keyword -> warning
    text = "前半" * 20 + "元気元気"
    issues = tracker.check_recovery_description(2, "Aki", text)
    assert len(issues) == 1
    assert "[回復描写不足]" in issues[0]
    # Recovered with recovery keyword -> ok
    text = "翌朝、元気元気"
    assert tracker.check_recovery_description(2, "Aki", text) == []


def test_check_stamina_jump(tracker):
    assert tracker.check_stamina_jump(2, "Aki", "元気に歩く。") == []
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                stamina_level="exhausted"))
    # exhausted(0) -> energetic(3): jump >= 2
    text = "前半" * 20 + "元気元気"
    issues = tracker.check_stamina_jump(2, "Aki", text)
    assert len(issues) == 1
    assert "[体力急変]" in issues[0]
    # exhausted(0) -> tired(1): no jump
    text = "前半" * 20 + "息が荒い息が荒い"
    assert tracker.check_stamina_jump(2, "Aki", text) == []


def test_check_psych_continuity(tracker):
    assert tracker.check_psych_continuity(2, "Aki", "安心して歩く。") == []
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                psych_state="distressed"))
    # distressed -> euphoric not allowed
    text = "前半" * 20 + "恍惚恍惚"
    issues = tracker.check_psych_continuity(2, "Aki", text)
    assert len(issues) == 1
    assert "[心理矛盾]" in issues[0]
    # distressed -> anxious is allowed
    text = "前半" * 20 + "不安不安"
    assert tracker.check_psych_continuity(2, "Aki", text) == []


def test_check_psych_trigger(tracker):
    assert tracker.check_psych_trigger(2, "Aki", "安心して歩く。") == []
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                psych_state="distressed"))
    # distressed -> content without trigger keyword -> warning
    text = "前半" * 40 + "安心安心"
    issues = tracker.check_psych_trigger(2, "Aki", text)
    assert len(issues) == 1
    assert "distressed→content" in issues[0]
    # With trigger keyword -> ok
    text = "前半" * 40 + "救われて安心安心"
    assert tracker.check_psych_trigger(2, "Aki", text) == []
    # euphoric -> distressed without trigger -> warning
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                psych_state="euphoric"))
    text = "前半" * 40 + "絶望絶望"
    issues = tracker.check_psych_trigger(2, "Aki", text)
    assert len(issues) == 1
    assert "euphoric→distressed" in issues[0]


def test_check_psych_jump(tracker):
    assert tracker.check_psych_jump(2, "Aki", "安心して歩く。") == []
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                psych_state="distressed"))
    # distressed(0) -> content(3): jump >= 2
    text = "前半" * 20 + "安心安心"
    issues = tracker.check_psych_jump(2, "Aki", text)
    assert len(issues) == 1
    assert "[心理急変]" in issues[0]
    # distressed(0) -> anxious(1): no jump
    text = "前半" * 20 + "不安不安"
    assert tracker.check_psych_jump(2, "Aki", text) == []


def test_check_clothing_continuity(tracker):
    assert tracker.check_clothing_continuity(2, "Aki", "着る。") == []
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                clothing_state="fully_undressed"))
    # Undressed + no time passage + no dress description -> warning
    text = "前半" * 60 + "会話をする。"
    issues = tracker.check_clothing_continuity(2, "Aki", text)
    assert len(issues) == 1
    assert "[衣服引き継ぎ矛盾]" in issues[0]
    # With time passage -> ok
    text = "翌朝、会話をする。"
    assert tracker.check_clothing_continuity(2, "Aki", text) == []
    # With dress verbs -> ok
    text = "前半" * 60 + "衣服を整える。"
    assert tracker.check_clothing_continuity(2, "Aki", text) == []
    # With dress keywords -> ok
    text = "前半" * 60 + "着直す。"
    assert tracker.check_clothing_continuity(2, "Aki", text) == []
    # Fully dressed previous state -> no check
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                clothing_state="fully_dressed"))
    assert tracker.check_clothing_continuity(2, "Aki", "会話をする。") == []


def test_check_intimacy_regression_and_rush(tracker):
    # No history
    assert tracker.check_intimacy_regression(2, "Aki", "信頼する。") == []
    assert tracker.check_intimacy_rush(2, "Aki", "信頼する。") == []
    # bonded(4) -> stranger(0): regression >= 2
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                intimacy_level="bonded"))
    issues = tracker.check_intimacy_regression(2, "Aki", "初対面のような距離。")
    assert len(issues) == 1
    assert "[親密度後退]" in issues[0]
    # stranger(0) -> bonded(4): rush >= 2
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                intimacy_level="stranger"))
    issues = tracker.check_intimacy_rush(2, "Aki", "運命の絆、一つに。")
    assert len(issues) == 1
    assert "[親密度急進]" in issues[0]
    # Small change -> no issues (close(2) -> acquaintance(1))
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                intimacy_level="close"))
    assert tracker.check_intimacy_regression(2, "Aki", "平穏な挨拶。") == []
    # close(2) -> stranger(0) is a 2-level regression -> warning
    issues = tracker.check_intimacy_regression(2, "Aki", "初対面の挨拶。")
    assert len(issues) == 1
    assert "close→stranger" in issues[0]
    # stranger(0) -> stranger(0) after rush check -> no issues
    assert tracker.check_intimacy_rush(2, "Aki", "初対面の挨拶。") == []


def test_check_intimacy_vs_erotic_level(tracker):
    assert tracker.check_intimacy_vs_erotic_level(2, "Aki", "口づけ。") == []
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                intimacy_level="stranger"))
    issues = tracker.check_intimacy_vs_erotic_level(2, "Aki", "肌を重ねる。")
    assert len(issues) == 1
    assert "[親密度不足]" in issues[0]
    # intimate level is fine
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                intimacy_level="intimate"))
    assert tracker.check_intimacy_vs_erotic_level(2, "Aki", "肌を重ねる。") == []


def test_check_location_continuity(tracker):
    assert tracker.check_location_continuity(2, "Aki", "部屋に戻る。") == []
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                location="indoor"))
    # Same location -> no issues
    text = "前半" * 60 + "部屋で話す。"
    assert tracker.check_location_continuity(2, "Aki", text) == []
    # Location change without transition/time -> warning
    text = "前半" * 60 + "森を歩く。"
    issues = tracker.check_location_continuity(2, "Aki", text)
    assert len(issues) == 1
    assert "[場所矛盾]" in issues[0]
    # With transition keyword -> ok
    text = "前半" * 60 + "森へ移動する。"
    assert tracker.check_location_continuity(2, "Aki", text) == []
    # With time passage -> ok
    text = "翌朝、森を歩く。"
    assert tracker.check_location_continuity(2, "Aki", text) == []
    # Unknown previous location -> skip
    tracker.save_snapshot(CharacterStateSnapshot(character_name="Aki", episode_num=1,
                                                location="unknown"))
    assert tracker.check_location_continuity(2, "Aki", "森を歩く。") == []


def test_check_environment_consistency(tracker):
    # Rain -> clear without time passage -> warning
    issues = tracker.check_environment_consistency("前半" * 30 + "雨が降る。", "前半" * 30 + "晴れている。")
    assert len(issues) == 1
    assert "[環境矛盾]" in issues[0]
    # With time passage -> ok
    issues = tracker.check_environment_consistency("雨が降る。", "翌朝、晴れている。")
    assert issues == []
    # Same weather -> ok
    issues = tracker.check_environment_consistency("雨が降る。", "雨が続く。")
    assert issues == []


def test_erotic_continuity_tracker_state_operations():
    from src.agents.erotic.continuity import EroticContinuityTracker

    erotic = EroticContinuityTracker()
    assert erotic.get_character_state("Aki") == {}
    erotic.update_character_state("Aki", {"position": "standing"})
    erotic.update_character_state("Aki", {"clothing": "undressed"})
    erotic.update_character_state("B", {"position": "sitting"})
    assert erotic.get_character_state("Aki") == {"position": "standing", "clothing": "undressed"}
    assert erotic.get_character_state("B") == {"position": "sitting"}
    assert erotic.get_character_state("Unknown") == {}
    # Returned dict is a copy
    state = erotic.get_character_state("Aki")
    state["position"] = "mutated"
    assert erotic.get_character_state("Aki")["position"] == "standing"
