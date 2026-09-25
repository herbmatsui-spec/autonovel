import sys
sys.path.insert(0, '.')
from src.models.subversion import SubversionEngine, SubversionPattern

# Test 1: Deterministic - same input produces same output
e1 = SubversionEngine(interval=3)
e1.plan_schedule(40)
e2 = SubversionEngine(interval=3)
e2.plan_schedule(40)

sched1 = [p.model_dump() for p in e1.schedule]
sched2 = [p.model_dump() for p in e2.schedule]
assert sched1 == sched2, "Deterministic test failed"
print("[OK] Deterministic: PASS")

# Test 2: Weight normalization
e3 = SubversionEngine(pattern_weights={"A": 0.9, "B": 0.2})
total = sum(e3.pattern_weights.values())
assert abs(total - 1.0) < 0.001, f"Weight normalization failed: {total}"
print("[OK] Weight normalization: PASS")

# Test 3: Interval changes schedule
e4 = SubversionEngine(interval=5)
e4.plan_schedule(20)
eps = [p.trigger_ep for p in e4.schedule]
assert eps == [5, 10, 15, 20], f"Interval test failed: {eps}"
print("[OK] Interval scheduling: PASS")

# Test 4: Disabled engine does nothing
e5 = SubversionEngine(enabled=False, interval=3)
e5.plan_schedule(10)
class Mock: pass
m = Mock()
result = e5.apply_to_arc(m, 3)
assert result is m
assert not hasattr(m, "subversion")
print("[OK] Disabled engine: PASS")

# Test 5: apply_to_arc sets thematic_milestone
e6 = SubversionEngine(interval=3)
e6.plan_schedule(10)
class MockArc:
    thematic_milestone = ""
arc = MockArc()
e6.apply_to_arc(arc, 3)
assert "裏切り" in arc.thematic_milestone
assert hasattr(arc, "subversion")
print("[OK] apply_to_arc: PASS")

# Test 6: apply_to_beat sets mission and tension
e7 = SubversionEngine(interval=3)
e7.plan_schedule(10)
class MockBeat:
    mission = ""
    visual_scene_focus = ""
    tension_target = 0.5
beat = MockBeat()
e7.apply_to_beat(beat, 3)
assert "裏切り" in beat.mission
assert "代償の可視化" in beat.visual_scene_focus
assert beat.tension_target == 0.8
print("[OK] apply_to_beat: PASS")

# Test 7: validate_coherence catches issues
e8 = SubversionEngine(interval=3)
e8.schedule = [
    SubversionPattern(pattern_type="A", trigger_ep=3, description="d", cost="c", payoff_hint="h"),
    SubversionPattern(pattern_type="B", trigger_ep=3, description="d", cost="c", payoff_hint="h"),  # duplicate
    SubversionPattern(pattern_type="C", trigger_ep=5, description="d", cost="c", payoff_hint="h"),  # interval < 3
    SubversionPattern(pattern_type="A", trigger_ep=38, description="d", cost="c", payoff_hint="h"), # too late
]
errors = e8.validate_coherence(40)
assert "重複発火話数あり" in errors
assert any("間隔不足" in err for err in errors)
assert any("終盤すぎる" in err for err in errors)
print("[OK] validate_coherence: PASS")

print("\n=== ALL MANUAL TESTS PASSED ===")