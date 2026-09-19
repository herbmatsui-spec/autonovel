"""Global Narrative Balancer orchestrating F1, F2, and F3 with arbitration."""

import logging
import time
from typing import Dict, List, Optional, Union
from src.narrative_balancer.arbitrator.applier import CorrectionApplier
from src.narrative_balancer.arbitrator.config import ArbitratorConfig, load_arbitrator_config
from src.narrative_balancer.arbitrator.models import BalancerResult, IntegratedResult, PlotState
from src.narrative_balancer.arbitrator.ports import CSPAdapter, DSPAdapter, GrammarAdapter, NarrativeBalancerPort
from src.narrative_balancer.arbitrator.resolver import PriorityResolver
from src.narrative_balancer.csp.balancer import CSPNarrativeBalancer
from src.narrative_balancer.models import Beat, ValidationResult

logger = logging.getLogger(__name__)


class GlobalNarrativeBalancer:
    """Master orchestrator synthesizing DSP, CSP, and Grammar balancing engines."""

    def __init__(self, config: Optional[ArbitratorConfig] = None):
        self.config = config or load_arbitrator_config()
        self.resolver = PriorityResolver(self.config)
        self.applier = CorrectionApplier()

        # Initialize adapters
        self.adapters: Dict[str, NarrativeBalancerPort] = {
            "grammar": GrammarAdapter(),
            "csp": CSPAdapter(),
            "dsp": DSPAdapter(),
        }
        self.csp_validator = CSPNarrativeBalancer()

    def balance(self, state_input: Union[PlotState, List[Beat]]) -> PlotState:
        """Execute full orchestration and return balanced PlotState."""
        integrated = self.orchestrate(state_input)
        return PlotState.from_beats(integrated.balanced_beats)

    def orchestrate(self, state_input: Union[PlotState, List[Beat]]) -> IntegratedResult:
        """Execute all enabled balancers, arbitrate conflicts, and return rich IntegratedResult."""
        t_start = time.perf_counter()

        if isinstance(state_input, list):
            plot_state = PlotState.from_beats(state_input)
        else:
            plot_state = state_input

        balancer_results: Dict[str, BalancerResult] = {}

        # Execute each enabled balancer
        for name, adapter in self.adapters.items():
            if self.config.enabled_balancers.get(name, True):
                try:
                    res = adapter.balance(plot_state)
                    balancer_results[name] = res
                except Exception as e:
                    logger.error(f"Balancer {name} execution failed: {e}")
                    balancer_results[name] = BalancerResult(
                        balancer_name=name,
                        beats=plot_state.beats,
                        success=False,
                        error_message=str(e),
                    )

        # Check if at least one balancer succeeded
        any_success = any(r.success for r in balancer_results.values())
        if not any_success:
            logger.warning("All balancers failed; falling back to original plot state.")
            return IntegratedResult(
                balanced_beats=[b.model_copy(deep=True) for b in plot_state.beats],
                applied_actions=[],
                conflicts=[],
                balancer_results=balancer_results,
                total_elapsed_ms=(time.perf_counter() - t_start) * 1000.0,
                is_valid=False,
            )

        # Resolve conflicts and merge
        resolved_beats, applied_actions, conflicts = self.resolver.resolve(plot_state, balancer_results)

        # Transactional application & invariant verification
        final_state = self.applier.apply(plot_state, resolved_beats)

        # Optional validation
        val_report: Optional[ValidationResult] = None
        if self.config.validate_output:
            val_report = self.csp_validator.validate_full(final_state.beats)

        elapsed = (time.perf_counter() - t_start) * 1000.0

        return IntegratedResult(
            balanced_beats=final_state.beats,
            applied_actions=applied_actions,
            conflicts=conflicts,
            balancer_results=balancer_results,
            total_elapsed_ms=round(elapsed, 2),
            is_valid=val_report.is_valid if val_report else True,
            validation_report=val_report,
        )

    def validate(self, state_input: Union[PlotState, List[Beat]]) -> ValidationResult:
        """Validate structural compliance."""
        beats = state_input.beats if isinstance(state_input, PlotState) else state_input
        return self.csp_validator.validate_full(beats)
