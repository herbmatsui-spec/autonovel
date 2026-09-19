import sys
sys.path.insert(0, '.')
from src.models.subversion import SubversionEngine, SubversionPattern
from src.models.plot import ArcBlueprint

# Test apply_to_arc directly
arc = ArcBlueprint(arc_num=1, start_ep=1, end_ep=10, title="Test", summary="Test")
print(f"Before: thematic_milestone='{arc.thematic_milestone}'")
print(f"Before: hasattr subversion={hasattr(arc, 'subversion')}")

engine = SubversionEngine(interval=3)
engine.plan_schedule(10)
print(f"Schedule: {[(p.trigger_ep, p.pattern_type) for p in engine.schedule]}")

for ep in range(1, 11):
    engine.apply_to_arc(arc, ep)

print(f"After: thematic_milestone='{arc.thematic_milestone}'")
print(f"After: hasattr subversion={hasattr(arc, 'subversion')}")
if hasattr(arc, 'subversion'):
    print(f"  subversion: {arc.subversion}")