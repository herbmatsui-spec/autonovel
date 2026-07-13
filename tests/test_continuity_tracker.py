import os
import pytest
from src.agents.erotic_integrity import (
    CharacterStateSnapshot, ContinuityTracker,
    EroticIntegrityChecker, ContinuityReport
)

@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_continuity.db"
    return str(db_file)

class TestCharacterStateSnapshot:
    def test_default_values(self):
        snap = CharacterStateSnapshot(character_name="テスト", episode_num=1)
        assert snap.stamina_level == "normal"
        assert snap.psych_state == "neutral"
        assert snap.clothing_state == "fully_dressed"
        assert snap.custom_flags == {}

    def test_custom_values(self):
        snap = CharacterStateSnapshot(
            character_name="花子", episode_num=3,
            stamina_level="exhausted", psych_state="euphoric"
        )
        assert snap.stamina_level == "exhausted"
        assert snap.psych_state == "euphoric"

class TestContinuityTracker:
    def test_save_and_get(self, temp_db):
        tracker = ContinuityTracker(db_path=temp_db)
        snap = CharacterStateSnapshot(character_name="花子", episode_num=1)
        tracker.save_snapshot(snap)
        result = tracker.get_snapshot(1, "花子")
        assert result is not None
        assert result.character_name == "花子"

    def test_get_previous(self, temp_db):
        tracker = ContinuityTracker(db_path=temp_db)
        snap = CharacterStateSnapshot(character_name="花子", episode_num=1, stamina_level="exhausted")
        tracker.save_snapshot(snap)
        prev = tracker.get_previous_snapshot(2, "花子")
        assert prev is not None
        assert prev.stamina_level == "exhausted"

    def test_get_nonexistent(self, temp_db):
        tracker = ContinuityTracker(db_path=temp_db)
        assert tracker.get_snapshot(99, "存在しない") is None

class TestStaminaChecks:
    def test_stamina_contradiction(self, temp_db):
        tracker = ContinuityTracker(db_path=temp_db)
        snap = CharacterStateSnapshot(
            character_name="花子", episode_num=1, stamina_level="exhausted"
        )
        tracker.save_snapshot(snap)

        text = "花子は元気に活力を持って走り出した。力が漲っていた。"
        issues = tracker.check_stamina_continuity(2, "花子", text)
        assert len(issues) > 0
        assert "体力矛盾" in issues[0]

    def test_stamina_natural_transition(self, temp_db):
        tracker = ContinuityTracker(db_path=temp_db)
        snap = CharacterStateSnapshot(
            character_name="花子", episode_num=1, stamina_level="exhausted"
        )
        tracker.save_snapshot(snap)

        text = "花子はまだ疲弊したまま、ぐったりと横たわっていた。"
        issues = tracker.check_stamina_continuity(2, "花子", text)
        assert len(issues) == 0

class TestPsychChecks:
    def test_psych_contradiction(self, temp_db):
        tracker = ContinuityTracker(db_path=temp_db)
        snap = CharacterStateSnapshot(
            character_name="太郎", episode_num=1, psych_state="distressed"
        )
        tracker.save_snapshot(snap)

        text = "太郎は恍惚とした表情で歓喜に包まれていた。至福の時だった。"
        issues = tracker.check_psych_continuity(2, "太郎", text)
        assert len(issues) > 0
        assert "心理矛盾" in issues[0]

class TestClothingContinuity:
    def test_clothing_contradiction(self, temp_db):
        tracker = ContinuityTracker(db_path=temp_db)
        snap = CharacterStateSnapshot(
            character_name="花子", episode_num=1,
            clothing_state="fully_undressed"
        )
        tracker.save_snapshot(snap)

        text = "花子は部屋の中を歩き回っていた。窓の外を眺めていた。"
        issues = tracker.check_clothing_continuity(2, "花子", text)
        assert len(issues) > 0
        assert "衣服引き継ぎ矛盾" in issues[0]

    def test_clothing_with_time_passage(self, temp_db):
        tracker = ContinuityTracker(db_path=temp_db)
        snap = CharacterStateSnapshot(
            character_name="花子", episode_num=1,
            clothing_state="fully_undressed"
        )
        tracker.save_snapshot(snap)

        text = "翌朝、花子は部屋の中を歩き回っていた。"
        issues = tracker.check_clothing_continuity(2, "花子", text)
        assert len(issues) == 0  # 翌朝 → 時間経過でリセット許容

class TestIntimacyContinuity:
    def test_intimacy_regression(self, temp_db):
        tracker = ContinuityTracker(db_path=temp_db)
        snap = CharacterStateSnapshot(
            character_name="花子", episode_num=1,
            intimacy_level="bonded"
        )
        tracker.save_snapshot(snap)

        text = "花子は初対面の見知らぬ相手のように振る舞った。他人行儀な態度だった。"
        issues = tracker.check_intimacy_regression(2, "花子", text)
        assert len(issues) > 0

class TestLocationContinuity:
    def test_location_contradiction(self, temp_db):
        tracker = ContinuityTracker(db_path=temp_db)
        snap = CharacterStateSnapshot(
            character_name="花子", episode_num=1, location="indoor"
        )
        tracker.save_snapshot(snap)

        text = "花子は外の森の中を歩いていた。空の下で鳥の声を聞いた。"
        issues = tracker.check_location_continuity(2, "花子", text)
        assert len(issues) > 0
        assert "場所矛盾" in issues[0]

class TestIntegration:
    def test_check_all_with_continuity(self, temp_db):
        checker = EroticIntegrityChecker(db_path=temp_db)

        # Episode 1 を完了
        ep1_text = (
            "花子は同意して身を委ねた。求めてと囁いた。"
            "【Build】彼女は緊張していた。"
            "【Peak】二人は肌を重ねた。"
            "【Afterglow】花子は疲弊して倒れ込んだ。限界だった。ぐったりとしていた。"
        )
        checker.finalize_episode("花子", 1, ep1_text)

        # Episode 2 を検証 (急激な体力回復)
        ep2_text = (
            "花子は元気に活力を持って走り出した。力が漲っていた。弾むような足取りだった。"
            "同意して求めてと言った。いいよと答えた。"
        )
        is_safe, issues, quality, continuity = checker.check_all(
            ep2_text, current_ep=2, character_name="花子", prev_text=ep1_text
        )

        assert continuity is not None
        assert not continuity.is_consistent
        assert any("体力矛盾" in i for i in continuity.issues)

    def test_check_all_backward_compatible(self, temp_db):
        """既存のcheck_all呼び出し（continuity引数なし）が動作することを確認。"""
        checker = EroticIntegrityChecker(db_path=temp_db)
        text = "彼女は同意して求めてと言った。いいよと答えた。"
        result = checker.check_all(text)
        assert len(result) == 4
        assert result[3] is None  # continuity_report は None
