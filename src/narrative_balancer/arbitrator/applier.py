"""Transactional application and validation of resolved beats."""

from typing import List
import numpy as np
from src.narrative_balancer.arbitrator.models import PlotState
from src.narrative_balancer.models import Beat


class CorrectionApplier:
    """Applies resolved beat sequences and enforces narrative invariant guarantees."""

    def apply(self, original_state: PlotState, resolved_beats: List[Beat]) -> PlotState:
        """Apply resolved beats atomically, verifying structural invariants."""
        # Deep copy
        new_beats = [b.model_copy(deep=True) for b in resolved_beats]

        # 1. Invariant: correct episode count
        if len(new_beats) != original_state.total_episodes:
            raise ValueError(
                f"Episode count mismatch: expected {original_state.total_episodes}, got {len(new_beats)}"
            )

        # 2. Invariant: monotonic episodes & valid tension bounds
        for i, b in enumerate(new_beats):
            expected_ep = i + 1
            if b.episode != expected_ep:
                b.episode = expected_ep

            # Tension bounding
            if b.tension is None or np.isnan(b.tension):
                b.tension = 5.0
            else:
                b.tension = float(np.clip(b.tension, 1.0, 10.0))

        return PlotState(
            total_episodes=original_state.total_episodes,
            beats=new_beats,
            characters=original_state.characters,
            metadata=dict(original_state.metadata),
        )
