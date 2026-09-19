# tests/test_subversion_engine.py
import pytest
from src.models.subversion import SubversionEngine, SubversionPattern


class TestSubversionEngine:
    def test_plan_schedule_deterministic(self):
        e1 = SubversionEngine(interval=3)
        e1.plan_schedule(12)
        e2 = SubversionEngine(interval=3)
        e2.plan_schedule(12)
        assert [p.model_dump() for p in e1.schedule] == [p.model_dump() for p in e2.schedule]

    def test_weight_normalization(self):
        e = SubversionEngine(pattern_weights={"A": 0.9, "B": 0.2})
        assert abs(sum(e.pattern_weights.values()) - 1.0) < 0.001

    def test_apply_to_arc(self):
        class MockArc: pass
        e = SubversionEngine(interval=3)
        e.plan_schedule(9)
        arc = MockArc()
        e.apply_to_arc(arc, 3)
        assert hasattr(arc, "subversion")
        assert arc.subversion.pattern_type in {"A", "B", "C"}
        # ep=4 はスキップ
        e.apply_to_arc(arc, 4)
        assert arc.subversion.trigger_ep == 3

    def test_apply_to_beat_tension_clip(self):
        class MockBeat:
            tension_target = 0.9
        e = SubversionEngine(interval=3)
        e.plan_schedule(6)
        beat = MockBeat()
        e.apply_to_beat(beat, 3)
        assert beat.tension_target == 1.0

    def test_validate_coherence(self):
        e = SubversionEngine(interval=3)
        e.schedule = [
            SubversionPattern(pattern_type="A", trigger_ep=3, description="d", cost="c", payoff_hint="h"),
            SubversionPattern(pattern_type="B", trigger_ep=3, description="d", cost="c", payoff_hint="h"),  # 重複
            SubversionPattern(pattern_type="C", trigger_ep=5, description="d", cost="c", payoff_hint="h"),  # 間隔不足
            SubversionPattern(pattern_type="A", trigger_ep=38, description="d", cost="c", payoff_hint="h"), # 終盤
        ]
        errors = e.validate_coherence(40)
        assert "重複発火話数あり" in errors
        assert any("間隔不足" in e for e in errors)
        assert any("終盤すぎる" in e for e in errors)

    def test_disabled(self):
        e = SubversionEngine(enabled=False, interval=3)
        e.plan_schedule(6)
        class Mock: pass
        assert e.apply_to_arc(Mock(), 3) is not None  # 何もしない
        assert e.apply_to_beat(Mock(), 3) is not None  # 何もしない

    def test_apply_to_beat_mission_and_focus(self):
        class MockBeat:
            mission = ""
            visual_scene_focus = ""
            tension_target = 0.5
        e = SubversionEngine(interval=3)
        e.plan_schedule(6)
        beat = MockBeat()
        e.apply_to_beat(beat, 3)
        assert "裏切り" in beat.mission
        assert "代償の可視化" in beat.visual_scene_focus
        assert beat.tension_target == 0.8  # 0.5 + 0.3

    def test_apply_to_arc_thematic_milestone(self):
        class MockArc:
            thematic_milestone = ""
        e = SubversionEngine(interval=3)
        e.plan_schedule(6)
        arc = MockArc()
        e.apply_to_arc(arc, 3)
        assert "裏切り" in arc.thematic_milestone
        assert hasattr(arc, "subversion")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])