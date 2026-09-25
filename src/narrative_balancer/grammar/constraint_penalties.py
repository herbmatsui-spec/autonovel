"""Constraint penalties for grammar-based narrative analysis."""

from typing import Dict, List, Optional
import numpy as np
from src.narrative_balancer.models import Beat


def char_neglect_penalty(beats: List[Beat], characters: Optional[List[str]] = None) -> float:
    """Penalize characters that have not appeared for more than 5 consecutive episodes."""
    if not beats:
        return 0.0

    chars = characters or ["Protagonist", "Rival", "Mentor"]
    total_penalty = 0.0

    for ch in chars:
        last_seen = -1
        for i, b in enumerate(beats):
            if ch in b.characters:
                last_seen = i
            else:
                gap = (i - last_seen) if last_seen != -1 else (i + 1)
                if gap > 5:
                    total_penalty += 1.5 * (gap - 5)

    return total_penalty


def payoff_decay_penalty(beats: List[Beat], max_distance: int = 15) -> float:
    """Penalize introduced foreshadowing setups that remain unresolved beyond max_distance."""
    unresolved: Dict[str, int] = {}
    penalty = 0.0

    for i, b in enumerate(beats):
        for s in b.foreshadowing_setup:
            unresolved[s] = i
        for p in b.foreshadowing_payoff:
            if p in unresolved:
                del unresolved[p]

        # Check age of unresolved items
        for setup_item, setup_idx in unresolved.items():
            age = i - setup_idx
            if age > max_distance:
                penalty += 2.0 * (age - max_distance)

    return penalty


def tension_monotony_penalty(beats: List[Beat]) -> float:
    """Penalize runs of 4 or more episodes with near-zero tension variance."""
    if len(beats) < 4:
        return 0.0

    tensions = [b.tension for b in beats]
    penalty = 0.0

    for i in range(len(tensions) - 3):
        window = tensions[i:i + 4]
        if np.var(window) < 0.2:
            penalty += 5.0

    return penalty
