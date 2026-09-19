"""Priority-based conflict resolution and synthesis engine."""

from typing import Dict, List, Tuple
from src.narrative_balancer.arbitrator.config import ArbitratorConfig
from src.narrative_balancer.arbitrator.models import BalancerResult, ConflictRecord, PlotState
from src.narrative_balancer.models import Beat, CorrectionAction


class PriorityResolver:
    """Synthesizes narrative attributes using a domain-specific hierarchy:

    - Beat Type & Macro Structure: Grammar > CSP > DSP
    - Character Arc & Defeats: CSP > Grammar > DSP
    - Tension Dynamics & Curves: DSP > CSP > Grammar
    """

    def __init__(self, config: ArbitratorConfig):
        self.config = config
        self.priority_order = config.priority_order

    def resolve(
        self,
        original_state: PlotState,
        results: Dict[str, BalancerResult],
    ) -> Tuple[List[Beat], List[CorrectionAction], List[ConflictRecord]]:
        final_beats: List[Beat] = []
        applied_actions: List[CorrectionAction] = []
        conflicts: List[ConflictRecord] = []

        total_eps = original_state.total_episodes
        orig_map = {b.episode: b for b in original_state.beats}

        for ep in range(1, total_eps + 1):
            base_beat = orig_map.get(ep, Beat(episode=ep))

            # Active balancer proposals for this episode
            proposals: Dict[str, Beat] = {}
            for name, res in results.items():
                if res.success:
                    for b in res.beats:
                        if b.episode == ep:
                            proposals[name] = b
                            break

            if not proposals:
                final_beats.append(base_beat.model_copy(deep=True))
                continue

            # Determine if any balancer differs from base or each other
            has_difference = any(
                prop.tension != base_beat.tension
                or prop.beat_type != base_beat.beat_type
                or prop.characters != base_beat.characters
                or prop.is_defeat != base_beat.is_defeat
                for prop in proposals.values()
            )

            if not has_difference:
                final_beats.append(base_beat.model_copy(deep=True))
                continue

            # Synthesize specialized attributes
            chosen_beat = base_beat.model_copy(deep=True)
            conflicting_names = []

            # 1. Beat Type: Grammar (primary) -> CSP (secondary) -> DSP (tertiary)
            bt_order = ["grammar", "csp", "dsp"]
            for name in bt_order:
                if name in proposals:
                    prop_bt = proposals[name].beat_type
                    if prop_bt != base_beat.beat_type:
                        conflicting_names.append(name)
                    # The highest priority available sets the beat type
                    chosen_beat.beat_type = prop_bt
                    chosen_beat.summary = proposals[name].summary or chosen_beat.summary
                    break

            # 2. Tension: Take DSP if active and changed, or highest recommended tension
            if "dsp" in proposals and proposals["dsp"].tension != base_beat.tension:
                chosen_beat.tension = proposals["dsp"].tension
                if "dsp" not in conflicting_names:
                    conflicting_names.append("dsp")
            else:
                # Max tension recommended by any balancer
                max_t = max(p.tension for p in proposals.values())
                chosen_beat.tension = max_t

            # 3. Characters & Defeats: CSP (primary) -> Grammar -> Base
            if "csp" in proposals:
                if proposals["csp"].characters:
                    chosen_beat.characters = proposals["csp"].characters
                chosen_beat.is_defeat = proposals["csp"].is_defeat

            final_beats.append(chosen_beat)

            # Record action
            if chosen_beat.beat_type != base_beat.beat_type or chosen_beat.tension != base_beat.tension:
                primary_winner = conflicting_names[0] if conflicting_names else "integrated"
                action = CorrectionAction(
                    episode=ep,
                    action_type=f"{primary_winner.upper()}_SYNTHESIZED_APPLY",
                    target_field="beat",
                    original_value=base_beat.beat_type.value,
                    new_value=chosen_beat.beat_type.value,
                    reason=f"Synthesized from {', '.join(proposals.keys())} with {primary_winner} priority",
                )
                applied_actions.append(action)

                if len(conflicting_names) > 1:
                    conflicts.append(ConflictRecord(
                        episode=ep,
                        conflicting_balancers=conflicting_names,
                        winning_balancer=primary_winner,
                        chosen_action=action,
                        rationale="Synthesized attributes according to domain expertise: Grammar for structure, CSP for arcs, DSP for tension.",
                    ))

        return final_beats, applied_actions, conflicts
