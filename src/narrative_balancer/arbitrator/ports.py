"""Ports and adapters for integrating F1, F2, and F3 balancers."""

import time
from typing import List, Protocol, runtime_checkable
from src.narrative_balancer.arbitrator.models import BalancerResult, PlotState
from src.narrative_balancer.csp.balancer import CSPNarrativeBalancer
from src.narrative_balancer.csp.partial_state import PartialPlotState
from src.narrative_balancer.dsp.balancer import DSPTensionBalancer
from src.narrative_balancer.grammar.balancer import GrammarNarrativeBalancer
from src.narrative_balancer.models import Beat, CorrectionAction


@runtime_checkable
class NarrativeBalancerPort(Protocol):
    """Protocol for unified balancer execution."""

    name: str

    def balance(self, state: PlotState) -> BalancerResult:
        ...


class DSPAdapter(NarrativeBalancerPort):
    """Adapts DSP Tension Balancer (F1) to NarrativeBalancerPort."""

    name = "dsp"

    def __init__(self, balancer: DSPTensionBalancer = None):
        self.balancer = balancer or DSPTensionBalancer()

    def balance(self, state: PlotState) -> BalancerResult:
        t0 = time.perf_counter()
        try:
            sags = self.balancer.analyze(state.beats)
            corrected = self.balancer.correct(state.beats)
            elapsed = (time.perf_counter() - t0) * 1000.0

            # Extract actions
            actions: List[CorrectionAction] = []
            for orig, corr in zip(state.beats, corrected):
                if orig.tension != corr.tension or orig.beat_type != corr.beat_type:
                    actions.append(CorrectionAction(
                        episode=orig.episode,
                        action_type="DSP_TENSION_ADJUST",
                        target_field="tension",
                        original_value=orig.tension,
                        new_value=corr.tension,
                        reason="DSP impulse correction of sagging section",
                    ))

            return BalancerResult(
                balancer_name=self.name,
                beats=corrected,
                actions=actions,
                detections_count=len(sags),
                confidence=0.85,
                elapsed_ms=round(elapsed, 2),
                success=True,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000.0
            return BalancerResult(
                balancer_name=self.name,
                beats=state.beats,
                elapsed_ms=round(elapsed, 2),
                success=False,
                error_message=str(e),
            )


class CSPAdapter(NarrativeBalancerPort):
    """Adapts CSP/SAT Balancer (F2) to NarrativeBalancerPort."""

    name = "csp"

    def __init__(self, balancer: CSPNarrativeBalancer = None):
        self.balancer = balancer or CSPNarrativeBalancer()

    def balance(self, state: PlotState) -> BalancerResult:
        t0 = time.perf_counter()
        try:
            partial = PartialPlotState.from_beats(state.beats, total_episodes=state.total_episodes)
            solved_beats = self.balancer.balance(partial)
            elapsed = (time.perf_counter() - t0) * 1000.0

            actions: List[CorrectionAction] = []
            orig_map = {b.episode: b for b in state.beats}
            for corr in solved_beats:
                orig = orig_map.get(corr.episode)
                if orig is None or orig.tension != corr.tension or orig.beat_type != corr.beat_type:
                    actions.append(CorrectionAction(
                        episode=corr.episode,
                        action_type="CSP_CONSTRAINT_SOLVE",
                        target_field="beat_type",
                        original_value=orig.beat_type.value if orig else None,
                        new_value=corr.beat_type.value,
                        reason="CP-SAT structural constraint satisfaction",
                    ))

            return BalancerResult(
                balancer_name=self.name,
                beats=solved_beats,
                actions=actions,
                detections_count=len(actions),
                confidence=0.90,
                elapsed_ms=round(elapsed, 2),
                success=True,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000.0
            return BalancerResult(
                balancer_name=self.name,
                beats=state.beats,
                elapsed_ms=round(elapsed, 2),
                success=False,
                error_message=str(e),
            )


class GrammarAdapter(NarrativeBalancerPort):
    """Adapts Grammar DP Balancer (F3) to NarrativeBalancerPort."""

    name = "grammar"

    def __init__(self, balancer: GrammarNarrativeBalancer = None):
        self.balancer = balancer or GrammarNarrativeBalancer()

    def balance(self, state: PlotState) -> BalancerResult:
        t0 = time.perf_counter()
        try:
            analysis = self.balancer.analyze_only(state.beats)
            balanced_beats = self.balancer.balance(state.beats, target_total_episodes=state.total_episodes)
            elapsed = (time.perf_counter() - t0) * 1000.0

            actions: List[CorrectionAction] = []
            for orig, corr in zip(state.beats, balanced_beats):
                if orig.beat_type != corr.beat_type or orig.tension != corr.tension:
                    actions.append(CorrectionAction(
                        episode=orig.episode,
                        action_type="GRAMMAR_REWRITE",
                        target_field="beat_type",
                        original_value=orig.beat_type.value,
                        new_value=corr.beat_type.value,
                        reason="Grammar structural rule rewrite (e.g. crisis injection)",
                    ))

            return BalancerResult(
                balancer_name=self.name,
                beats=balanced_beats,
                actions=actions,
                detections_count=len(analysis.pending_nonterminals),
                confidence=0.95,
                elapsed_ms=round(elapsed, 2),
                success=True,
            )
        except Exception as e:
            elapsed = (time.perf_counter() - t0) * 1000.0
            return BalancerResult(
                balancer_name=self.name,
                beats=state.beats,
                elapsed_ms=round(elapsed, 2),
                success=False,
                error_message=str(e),
            )
