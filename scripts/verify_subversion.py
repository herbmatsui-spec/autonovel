# scripts/verify_subversion.py
from src.models.subversion import SubversionEngine

engine = SubversionEngine(interval=3)
engine.plan_schedule(40)
for p in engine.schedule:
    print(f"Ep{p.trigger_ep:2d} [{p.pattern_type}] {p.description}")
    print(f"    Cost: {p.cost}")
    print(f"    Payoff: {p.payoff_hint}")
print("\nValidation:", engine.validate_coherence(40))