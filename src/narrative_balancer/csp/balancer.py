"""Main CSP Narrative Balancer."""

from typing import List, Optional, Union
from pathlib import Path
from src.narrative_balancer.csp.config import CSPConfig, load_csp_config
from src.narrative_balancer.csp.partial_state import PartialPlotState
from src.narrative_balancer.csp.repair import repair_midpoint_sag
from src.narrative_balancer.models import Beat, ValidationResult


class CSPNarrativeBalancer:
    """Constraint Satisfaction Problem (CSP) / SAT solver for story plot structure."""

    def __init__(self, config: Optional[CSPConfig] = None):
        if config is None:
            default_path = Path("config/csp_balancer.yaml")
            if default_path.exists():
                self.config = load_csp_config(default_path)
            else:
                self.config = CSPConfig()
        else:
            self.config = config

    def balance(self, state: Union[PartialPlotState, List[Beat]]) -> List[Beat]:
        """Repair or complete plot beats to satisfy all structural and quality constraints."""
        if isinstance(state, list):
            partial = PartialPlotState.from_beats(state, total_episodes=self.config.n_episodes)
        else:
            partial = state

        repaired_state = repair_midpoint_sag(partial, self.config)
        return repaired_state.to_beat_list()

    def validate_full(self, beats: List[Beat]) -> ValidationResult:
        """Validate a full 40-episode beat sheet against hard constraints."""
        violations: List[str] = []
        if len(beats) < self.config.n_episodes:
            violations.append(f"Expected {self.config.n_episodes} episodes, got {len(beats)}")

        beat_map = {b.episode: b for b in beats}

        # Midpoint check
        mid_ep = self.config.midpoint_episode
        if mid_ep in beat_map and beat_map[mid_ep].tension < self.config.midpoint_min_tension:
            violations.append(f"Midpoint (Ep {mid_ep}) tension {beat_map[mid_ep].tension} < {self.config.midpoint_min_tension}")

        # Climax check
        climax_ep = self.config.climax_episode
        if climax_ep in beat_map and beat_map[climax_ep].tension < self.config.climax_min_tension:
            violations.append(f"Climax (Ep {climax_ep}) tension {beat_map[climax_ep].tension} < {self.config.climax_min_tension}")

        return ValidationResult(
            is_valid=len(violations) == 0,
            violations=violations,
            score=max(0.0, 1.0 - (len(violations) * 0.2)),
        )
