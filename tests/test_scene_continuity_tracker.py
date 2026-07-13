import pytest
import sqlite3
import os
from src.agents.erotic_integrity import (
    SceneContinuityTracker, 
    SceneStateSnapshot, 
    SceneTypeDetector
)

@pytest.fixture
def temp_db(tmp_path):
    db_path = tmp_path / "test_scene_continuity.db"
    return str(db_path)

class TestSceneContinuityTracker:
    def test_save_and_get_snapshot(self, temp_db):
        tracker = SceneContinuityTracker(db_path=temp_db)
        snapshot = SceneStateSnapshot(
            character_name="Alice",
            episode_num=1,
            scene_type="combat",
            injury_level="moderate",
            attitude="hostile",
            discoveries=["ancient key"],
            travel_state="stable",
            recovery_state="exhausted",
            perspective="standard",
            foreshadowing_active=True,
            time_of_day="night",
            items_held=["sword", "shield"]
        )
        
        tracker.save_snapshot(snapshot)
        retrieved = tracker.get_snapshot(1, "Alice")
        
        assert retrieved is not None
        assert retrieved.character_name == "Alice"
        assert retrieved.injury_level == "moderate"
        assert "ancient key" in retrieved.discoveries
        assert retrieved.time_of_day == "night"
        assert "sword" in retrieved.items_held

    def test_get_previous_snapshot(self, temp_db):
        tracker = SceneContinuityTracker(db_path=temp_db)
        snap1 = SceneStateSnapshot(character_name="Alice", episode_num=1, scene_type="conversation", attitude="friendly")
        snap2 = SceneStateSnapshot(character_name="Alice", episode_num=2, scene_type="conversation", attitude="neutral")
        
        tracker.save_snapshot(snap1)
        tracker.save_snapshot(snap2)
        
        prev = tracker.get_previous_snapshot(2, "Alice")
        assert prev is not None
        assert prev.episode_num == 1
        assert prev.attitude == "friendly"

    def test_injury_continuity(self, temp_db):
        tracker = SceneContinuityTracker(db_path=temp_db)
        # Ep 1: Severe injury
        snap1 = SceneStateSnapshot(character_name="Bob", episode_num=1, scene_type="combat", injury_level="severe")
        tracker.save_snapshot(snap1)
        
        # Ep 2: Suddenly "none" without recovery
        text_ep2 = "ボブは元気に走り出した。"
        issues = tracker.check_injury_continuity(2, "Bob", text_ep2)
        assert any("不自然に回復" in issue for issue in issues)

    def test_attitude_continuity(self, temp_db):
        tracker = SceneContinuityTracker(db_path=temp_db)
        # Ep 1: Hostile
        snap1 = SceneStateSnapshot(character_name="Charlie", episode_num=1, scene_type="conversation", attitude="hostile")
        tracker.save_snapshot(snap1)
        
        # Ep 2: Suddenly "friendly" without transition
        text_ep2 = "チャーリーはにこやかに微笑んだ。"
        issues = tracker.check_attitude_continuity(2, "Charlie", text_ep2)
        assert any("態度が不自然に変化" in issue for issue in issues)

    def test_discovery_continuity(self, temp_db):
        tracker = SceneContinuityTracker(db_path=temp_db)
        # Ep 1: Found a secret map
        snap1 = SceneStateSnapshot(character_name="Dave", episode_num=1, scene_type="exploration", discoveries=["秘密の地図"])
        tracker.save_snapshot(snap1)
        
        # Ep 2: Map is forgotten/not mentioned in a discovery scene
        text_ep2 = "デイブは洞窟を探索したが、何も見つからなかった。"
        issues = tracker.check_discovery_continuity(2, "Dave", text_ep2)
        # Note: The current implementation warns if previous discoveries are not mentioned 
        # when the current scene is also "exploration" (or similar)
        # Actually, check_discovery_continuity checks if prev_snapshot.discoveries are in text.
        assert any("秘密の地図" in issue for issue in issues)

    def test_travel_continuity(self, temp_db):
        tracker = SceneContinuityTracker(db_path=temp_db)
        # Ep 1: Departing
        snap1 = SceneStateSnapshot(character_name="Eve", episode_num=1, scene_type="travel", travel_state="departing")
        tracker.save_snapshot(snap1)
        
        # Ep 2: No mention of arrival but state is now "stable"
        text_ep2 = "イヴは森の中で休息していた。"
        issues = tracker.check_travel_continuity(2, "Eve", text_ep2)
        assert any("到着の描写" in issue for issue in issues)

    def test_recovery_continuity(self, temp_db):
        tracker = SceneContinuityTracker(db_path=temp_db)
        # Ep 1: Exhausted
        snap1 = SceneStateSnapshot(character_name="Frank", episode_num=1, scene_type="rest", recovery_state="exhausted")
        tracker.save_snapshot(snap1)
        
        # Ep 2: Suddenly fighting intensely without recovery
        text_ep2 = "フランクは猛烈な勢いで剣を振るった。"
        issues = tracker.check_recovery_continuity(2, "Frank", text_ep2)
        assert any("回復描写がないまま" in issue for issue in issues)

    def test_perspective_continuity(self, temp_db):
        tracker = SceneContinuityTracker(db_path=temp_db)
        # Ep 1: First person
        snap1 = SceneStateSnapshot(character_name="Grace", episode_num=1, scene_type="monologue", perspective="first_person")
        tracker.save_snapshot(snap1)
        
        # Ep 2: Third person
        text_ep2 = "グレースは静かに空を見上げた。"
        issues = tracker.check_perspective_continuity(2, "Grace", text_ep2)
        assert any("視点が変更" in issue for issue in issues)

    def test_time_continuity(self, temp_db):
        tracker = SceneContinuityTracker(db_path=temp_db)
        # Ep 1: Night
        snap1 = SceneStateSnapshot(character_name="Heidi", episode_num=1, scene_type="time", time_of_day="night")
        tracker.save_snapshot(snap1)
        
        # Ep 2: Day (without transition keywords)
        text_ep2 = "太陽が真上にある。ハイディは歩き出した。"
        issues = tracker.check_time_continuity(2, "Heidi", text_ep2)
        assert any("不自然に遷移" in issue for issue in issues)

    def test_item_continuity(self, temp_db):
        tracker = SceneContinuityTracker(db_path=temp_db)
        # Ep 1: Holding "聖剣"
        snap1 = SceneStateSnapshot(character_name="Ivan", episode_num=1, scene_type="item", items_held=["聖剣"])
        tracker.save_snapshot(snap1)
        
        # Ep 2: No mention of "聖剣" and no loss keywords
        text_ep2 = "イヴァンはただ立っていた。"
        issues = tracker.check_item_continuity(2, "Ivan", text_ep2)
        assert any("聖剣' が前話から消失" in issue for issue in issues)

    def test_extract_snapshot_integration(self, temp_db):
        tracker = SceneContinuityTracker(db_path=temp_db)
        text = "夜の森で、ボブは深い傷を負いながらも聖剣を握りしめ、敵意を剥き出しにしていた。彼は一人で絶望していた。"
        #- 夜 -> night
        #- 深い傷 -> severe
        #- 聖剣 -> items: ["聖剣"]
        #- 敵意 -> hostile
        #- 一人で絶望 (独白風) -> perspective: first_person (assuming keywords match)
        
        snap = tracker.extract_snapshot(text)
        assert snap.time_of_day == "night"
        assert snap.injury_level == "severe"
        assert "聖剣" in snap.items_held
        assert snap.attitude == "hostile"

    def test_check_all_continuity(self, temp_db):
        tracker = SceneContinuityTracker(db_path=temp_db)
        # Setup a contradictory state
        snap1 = SceneStateSnapshot(
            character_name="Alice", episode_num=1, scene_type="mixed",
            injury_level="severe", attitude="hostile", items_held=["聖剣"], time_of_day="night"
        )
        tracker.save_snapshot(snap1)
        
        text_ep2 = "翌朝、アリスは聖剣を忘れ、にこやかに微笑んで走り出した。"
        # - 聖剣消失 (Issue)
        # - 態度変化 hostile -> friendly (Issue)
        # - 回復 severe -> none (Issue)
        # - 時間遷移 night -> morning (OK since "翌朝" is there)
        
        issues = tracker.check_all_continuity(2, "Alice", text_ep2)
        assert len(issues) >= 3
