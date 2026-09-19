import sys
sys.path.insert(0, '.')
from src.models.subversion import SubversionEngine, SubversionPattern

e = SubversionEngine(interval=3)
e.plan_schedule(12)

# Test serialization roundtrip
dumped = e.model_dump()
print('Dumped keys:', list(dumped.keys()))
print('Schedule count:', len(dumped['schedule']))

# Test pattern dump
for p in e.schedule:
    pd = p.model_dump()
    print(f'  Pattern: type={pd["pattern_type"]}, ep={pd["trigger_ep"]}')

# Test validate
print('Validation:', e.validate_coherence(12))