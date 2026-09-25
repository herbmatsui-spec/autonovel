"""Grammar rewrite rules for transforming deficient narrative sequences."""

from dataclasses import dataclass
from typing import Callable, List, Optional
from src.narrative_balancer.grammar.symbols import Terminal


@dataclass
class RewriteRule:
    name: str
    pattern: List[Terminal]
    replacement: List[Terminal]
    priority: int
    condition: Optional[Callable[[int, int], bool]] = None  # (position, total_episodes) -> bool


def _is_mid_story(pos: int, total: int) -> bool:
    """Check if position is roughly in the middle portion (30% to 70%)."""
    return int(total * 0.3) <= pos <= int(total * 0.7)


REWRITE_RULES: List[RewriteRule] = [
    # 1. Stagnation in mid-story -> Midpoint Disaster
    RewriteRule(
        name="StagnationToMidpointDisaster",
        pattern=[Terminal.STAGNATION],
        replacement=[Terminal.MIDPOINT_DISASTER],
        priority=100,
        condition=_is_mid_story,
    ),
    # 2. Triple daily episodes in mid-story -> insert disaster on 3rd
    RewriteRule(
        name="TripleDailyToDisaster",
        pattern=[Terminal.DAILY, Terminal.DAILY, Terminal.DAILY],
        replacement=[Terminal.DAILY, Terminal.DAILY, Terminal.MIDPOINT_DISASTER],
        priority=90,
        condition=_is_mid_story,
    ),
    # 3. Triple rising episodes without climax -> insert midpoint turn
    RewriteRule(
        name="TripleRisingBreakthrough",
        pattern=[Terminal.RISING, Terminal.RISING, Terminal.RISING],
        replacement=[Terminal.RISING, Terminal.MIDPOINT_DISASTER, Terminal.FALLOUT],
        priority=80,
        condition=_is_mid_story,
    ),
]
