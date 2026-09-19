"""Debug: final vector values."""
import sys

sys.path.insert(0, ".")

from src.pipeline.emotional_residue import EmotionType  # noqa: E402
from src.rules.engine import RuleEngine  # noqa: E402
from src.rules.rule_loader import DEFAULT_EVENTS_PATH, DEFAULT_RULES_PATH, RuleLoader, parse_episode_events  # noqa: E402
from src.rules.state_machine import EmotionalStateMachine  # noqa: E402

rules = RuleLoader().load_rules(DEFAULT_RULES_PATH)
engine = RuleEngine(rules=rules, state_machine=EmotionalStateMachine())
events_by_ep = parse_episode_events(DEFAULT_EVENTS_PATH)
snapshot = None
prev_ep = None
for ep in (14, 15, 16):
    engine.process_episode(ep, events_by_ep[ep], previous_snapshot=snapshot, previous_episode=prev_ep)
    snapshot = engine.last_snapshot
    prev_ep = ep
v = engine.last_vector
for (s, t, emo), val in sorted(v.signals.items()):
    print(f"{s}->{t} [{emo.value}]: {val:.4f}")
