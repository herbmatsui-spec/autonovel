"""Supplementary unit tests covering remaining narrative_balancer gaps.

Targets: csp.diagnostics, dsp.spectral / detector / signal / factory / config,
grammar.corrector / constraint_penalties / dp reconstruction, arbitrator balancer paths.
"""

import math
from pathlib import Path

import numpy as np
import pytest

from src.narrative_balancer.arbitrator.balancer import GlobalNarrativeBalancer
from src.narrative_balancer.arbitrator.config import (
    ArbitratorConfig,
    load_arbitrator_config,
)
from src.narrative_balancer.arbitrator.models import (
    BalancerResult,
    PlotState,
)
from src.narrative_balancer.csp.diagnostics import explain_infeasibility
from src.narrative_balancer.csp.partial_state import PartialPlotState
from src.narrative_balancer.dsp.config import load_dsp_config
from src.narrative_balancer.dsp.detector import detect_sag, detect_sag_in_window, scan_sags
from src.narrative_balancer.dsp.factory import create_dsp_balancer
from src.narrative_balancer.dsp.models import DSPConfig
from src.narrative_balancer.dsp.signal import extract_tension_curve
from src.narrative_balancer.dsp.spectral import (
    compute_psd,
    low_freq_energy_ratio,
    multivariate_spectral_flatness,
    spectral_flatness,
)
from src.narrative_balancer.grammar.constraint_penalties import (
    char_neglect_penalty,
    payoff_decay_penalty,
    tension_monotony_penalty,
)
from src.narrative_balancer.grammar.corrector import force_midpoint_correction
from src.narrative_balancer.grammar.cost_model import load_cost_model
from src.narrative_balancer.grammar.dp import (
    DPTable,
    build_dp_table,
    min_completion_cost,
    reconstruct_optimal_expansion,
)
from src.narrative_balancer.grammar.parse_forest import ParseForest
from src.narrative_balancer.models import Beat, BeatType


def _beat(ep: int, tension=5.0, bt: BeatType = BeatType.SETUP, chars=None, setups=None, payoffs=None) -> Beat:
    return Beat(
        episode=ep,
        tension=tension,
        beat_type=bt,
        characters=chars or [],
        foreshadowing_setup=setups or [],
        foreshadowing_payoff=payoffs or [],
    )


# ---------------------------------------------------------------- dsp.spectral
class TestSpectral:
    def test_compute_psd_empty(self):
        assert len(compute_psd(np.array([]))) == 0

    def test_compute_psd_basic(self):
        psd = compute_psd(np.array([1.0, 2.0, 3.0, 4.0]))
        assert psd.shape[0] == 3  # rfft one-sided
        assert np.all(psd >= 0)

    def test_spectral_flatness_short_curve(self):
        assert spectral_flatness(np.array([1.0])) == 0.0

    def test_spectral_flatness_constant_curve(self):
        # Constant signal: PSD is all ~0 (< eps) -> returns 0.0
        val = spectral_flatness(np.array([5.0, 5.0, 5.0, 5.0]))
        assert 0.0 <= val < 1e-6

    def test_spectral_flatness_white_noise_high(self):
        rng = np.random.default_rng(42)
        noise = rng.uniform(0, 10, 64)
        val = spectral_flatness(noise)
        assert 0.0 <= val <= 1.0

    def test_low_freq_ratio_short_curve(self):
        assert low_freq_energy_ratio(np.array([3.0])) == 1.0

    def test_low_freq_ratio_constant(self):
        # Zero dynamic energy -> fallback 1.0
        assert low_freq_energy_ratio(np.array([4.0, 4.0, 4.0])) == 1.0

    def test_low_freq_ratio_bounds(self):
        rng = np.random.default_rng(7)
        sig = rng.uniform(0, 10, 32)
        val = low_freq_energy_ratio(sig)
        assert 0.0 <= val <= 1.0

    def test_multivariate_flatness_1d_passthrough(self):
        arr = np.array([1.0, 2.0, 3.0, 4.0])
        assert multivariate_spectral_flatness(arr) == spectral_flatness(arr)

    def test_multivariate_flatness_2d(self):
        curves = np.array([[1.0, 2.0, 3.0, 4.0], [5.0, 5.0, 5.0, 5.0]])
        val = multivariate_spectral_flatness(curves)
        assert 0.0 <= val <= 1.0

    def test_multivariate_flatness_empty_channels(self):
        curves = np.zeros((0, 4))
        assert multivariate_spectral_flatness(curves) == 0.0


# ---------------------------------------------------------------- dsp.detector
class TestDetector:
    def test_window_too_short(self):
        is_sag, flat, low, reason = detect_sag_in_window(np.array([5.0, 5.0]), DSPConfig())
        assert is_sag is False
        assert reason == "Window too short"

    def test_low_variance_plateau(self):
        window = np.array([3.0, 3.1, 3.0, 3.05])
        is_sag, _, _, reason = detect_sag_in_window(window, DSPConfig())
        assert is_sag is True
        assert "plateau" in reason

    def test_high_flatness_and_low_freq(self):
        # Condition 2 branch: lower thresholds relative to the measured values
        window = np.array([8.0, 8.5, 8.2, 8.4, 8.1, 8.3, 8.0, 8.2])
        flat = spectral_flatness(window)
        low = low_freq_energy_ratio(window)
        cfg = DSPConfig(flatness_threshold=flat * 0.9, low_freq_ratio_threshold=low * 0.9)
        is_sag, _, _, reason = detect_sag_in_window(window, cfg)
        assert is_sag is True
        assert "flatness" in reason

    def test_prolonged_trough(self):
        # mean < 4.5 with high low-frequency dominance (condition 3 requires var >= 0.25)
        window = np.array([1.0, 1.5, 4.0, 4.5, 4.2, 4.0, 1.2, 1.5])
        is_sag, _, _, reason = detect_sag_in_window(window, DSPConfig())
        assert is_sag is True
        assert "trough" in reason

    def test_normal_dynamics(self):
        window = np.array([5.0, 8.0, 3.0, 9.0, 2.0, 7.0])
        is_sag, _, _, reason = detect_sag_in_window(window, DSPConfig())
        assert is_sag is False
        assert reason == "Normal dynamics"

    def test_detect_sag_short_sequence_guard(self):
        curve = np.array([3.0, 3.0, 3.0])
        assert detect_sag(curve, 0, DSPConfig()) is True

    def test_detect_sag_window_no_sag(self):
        curve = np.array([5.0, 8.0, 3.0, 9.0, 2.0, 7.0, 8.0, 3.0])
        assert detect_sag(curve, 7, DSPConfig()) is False

    def test_scan_sags_short_curve(self):
        assert scan_sags(np.array([1.0, 2.0, 3.0]), DSPConfig()) == []

    def test_scan_sags_finds_plateau(self):
        # 10 episodes: first 8 flat low tension, then rising
        curve = np.array([3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 8.0, 9.0])
        detections = scan_sags(curve, DSPConfig())
        assert len(detections) >= 1
        d = detections[0]
        assert d.is_sag is True
        assert d.start_episode >= 1
        assert d.end_episode <= len(curve)


# ---------------------------------------------------------------- dsp.signal
class TestSignal:
    def test_empty_beats(self):
        assert len(extract_tension_curve([])) == 0

    def test_nan_interpolated(self):
        beats = [_beat(1, 4.0), _beat(2, None), _beat(3, 8.0)]
        arr = extract_tension_curve(beats)
        assert not np.isnan(arr).any()
        assert arr[1] == pytest.approx(6.0)

    def test_all_nan_defaults(self):
        beats = [_beat(1, None), _beat(2, None)]
        arr = extract_tension_curve(beats)
        assert np.all(arr == 5.0)

    def test_plain_values(self):
        beats = [_beat(1, 2.0), _beat(2, 7.5)]
        arr = extract_tension_curve(beats)
        assert arr[0] == 2.0 and arr[1] == 7.5


# ---------------------------------------------------------------- dsp.factory/config
class TestDspFactory:
    def test_explicit_config_path_missing_raises(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            load_dsp_config(tmp_path / "nope.yaml")

    def test_load_dsp_config_valid(self, tmp_path: Path):
        cfg_file = tmp_path / "dsp.yaml"
        cfg_file.write_text("window_size: 6\nflatness_threshold: 0.7\n", encoding="utf-8")
        cfg = load_dsp_config(cfg_file)
        assert cfg.window_size == 6
        assert cfg.flatness_threshold == 0.7

    def test_create_dsp_balancer_explicit_path(self, tmp_path: Path):
        cfg_file = tmp_path / "dsp.yaml"
        cfg_file.write_text("window_size: 5\n", encoding="utf-8")
        balancer = create_dsp_balancer(cfg_file)
        assert balancer.config.window_size == 5

    def test_create_dsp_balancer_default_no_file(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        balancer = create_dsp_balancer()
        assert isinstance(balancer.config, DSPConfig)


# ---------------------------------------------------------------- csp.diagnostics
class TestDiagnostics:
    def test_no_conflicts(self):
        partial = PartialPlotState.from_beats([_beat(1, 5.0), _beat(2, 5.0)])
        conflicts = explain_infeasibility(partial, type("C", (), {
            "midpoint_episode": 20,
            "midpoint_min_tension": 7,
            "all_is_lost_episode": 30,
            "all_is_lost_max_tension": 4,
        })())
        assert conflicts == []

    def test_midpoint_conflict(self):
        partial = PartialPlotState.from_beats([_beat(20, 3.0)])
        conflicts = explain_infeasibility(partial, type("C", (), {
            "midpoint_episode": 20,
            "midpoint_min_tension": 7,
            "all_is_lost_episode": 30,
            "all_is_lost_max_tension": 4,
        })())
        assert len(conflicts) == 1
        assert conflicts[0].constraint_name == "MidpointDisasterTension"

    def test_all_is_lost_conflict(self):
        partial = PartialPlotState.from_beats([_beat(30, 8.0)])
        conflicts = explain_infeasibility(partial, type("C", (), {
            "midpoint_episode": 20,
            "midpoint_min_tension": 7,
            "all_is_lost_episode": 30,
            "all_is_lost_max_tension": 4,
        })())
        assert len(conflicts) == 1
        assert conflicts[0].constraint_name == "AllIsLostTrough"

    def test_tension_jump_conflict(self):
        partial = PartialPlotState.from_beats([_beat(10, 2.0), _beat(11, 9.0)])
        conflicts = explain_infeasibility(partial, type("C", (), {
            "midpoint_episode": 20,
            "midpoint_min_tension": 7,
            "all_is_lost_episode": 30,
            "all_is_lost_max_tension": 4,
        })())
        assert any(c.constraint_name == "TensionPhysicsDelta" for c in conflicts)


# ---------------------------------------------------------------- grammar
class TestGrammarCorrector:
    def test_force_midpoint_empty(self):
        assert force_midpoint_correction([], ep=20) == []

    def test_force_midpoint_replaces_setup(self):
        beats = [_beat(i, 4.0, BeatType.SETUP) for i in range(1, 11)]
        result = force_midpoint_correction(beats, ep=5)
        assert result[4].beat_type == BeatType.MIDPOINT_DISASTER
        assert result[4].tension == 9.0
        # Other beats unchanged
        assert result[0].beat_type == BeatType.SETUP

    def test_force_midpoint_keeps_existing_disaster(self):
        beats = [_beat(1, 4.0, BeatType.SETUP), _beat(2, 9.0, BeatType.MIDPOINT_DISASTER)]
        result = force_midpoint_correction(beats, ep=2)
        assert result[1].beat_type == BeatType.MIDPOINT_DISASTER


class TestConstraintPenalties:
    def test_char_neglect_empty(self):
        assert char_neglect_penalty([]) == 0.0

    def test_char_neglect_gap(self):
        beats = [
            _beat(1, 5.0, chars=["Protagonist"]),
            _beat(2, 5.0, chars=[]),
            _beat(3, 5.0, chars=[]),
            _beat(4, 5.0, chars=[]),
            _beat(5, 5.0, chars=[]),
            _beat(6, 5.0, chars=[]),
            _beat(7, 5.0, chars=[]),
            _beat(8, 5.0, chars=[]),
        ]
        penalty = char_neglect_penalty(beats, characters=["Protagonist"])
        assert penalty > 0.0

    def test_char_neglect_no_gap(self):
        beats = [_beat(1, 5.0, chars=["Protagonist"]), _beat(2, 5.0, chars=["Protagonist"])]
        assert char_neglect_penalty(beats, characters=["Protagonist"]) == 0.0

    def test_payoff_decay_unresolved(self):
        beats = [_beat(1, 5.0, setups=["X"])]
        # item never paid off; iterate only over provided beats
        assert payoff_decay_penalty(beats) >= 0.0

    def test_payoff_decay_resolved(self):
        beats = [_beat(1, 5.0, setups=["X"]), _beat(2, 5.0, payoffs=["X"])]
        assert payoff_decay_penalty(beats) == 0.0

    def test_tension_monotony_short(self):
        assert tension_monotony_penalty([_beat(1), _beat(2), _beat(3)]) == 0.0

    def test_tension_monotony_flat_window(self):
        # 5 beats -> 2 overlapping 4-episode windows, each penalized 5.0
        beats = [_beat(i, 5.0) for i in range(1, 6)]
        assert tension_monotony_penalty(beats) == 10.0

    def test_tension_monotony_varied(self):
        beats = [_beat(1, 2.0), _beat(2, 8.0), _beat(3, 3.0), _beat(4, 9.0), _beat(5, 1.0)]
        assert tension_monotony_penalty(beats) == 0.0


class TestGrammarDP:
    def test_dp_table_terminal_base(self):
        dp = build_dp_table(max_len=5)
        assert _get_terminal_cost(dp) == 0.0

    def test_min_completion_cost_zero_remaining(self):
        forest = ParseForest(consumed_terminals=0)
        assert min_completion_cost(forest, 0) == 0.0

    def test_min_completion_cost_zero_remaining_with_pending(self):
        from src.narrative_balancer.grammar.symbols import NonTerminal

        forest = ParseForest(consumed_terminals=0, pending_nonterminals={NonTerminal.STAGNATION_RULE})
        cost = min_completion_cost(forest, 0)
        assert cost == pytest.approx(25.0)

    def test_min_completion_cost_with_remaining(self):
        from src.narrative_balancer.grammar.symbols import NonTerminal

        forest = ParseForest(consumed_terminals=0, pending_nonterminals={NonTerminal.ACT3})
        cost = min_completion_cost(forest, 6)
        assert cost >= 0.0

    def test_min_completion_cost_no_pending(self):
        forest = ParseForest(consumed_terminals=0)
        cost = min_completion_cost(forest, 8)
        assert cost >= 0.0

    def test_reconstruct_terminal_passthrough(self):
        from src.narrative_balancer.grammar.symbols import Terminal

        dp = DPTable(load_cost_model(), max_len=4)
        result = reconstruct_optimal_expansion(dp, Terminal.SETUP, 3)
        assert result == [Terminal.SETUP, Terminal.SETUP, Terminal.SETUP]

    def test_reconstruct_fallback(self):
        from src.narrative_balancer.grammar.symbols import NonTerminal, Terminal

        dp = DPTable(load_cost_model(), max_len=4)
        result = reconstruct_optimal_expansion(dp, NonTerminal.ACT3, 5)
        assert result[0] == Terminal.SETUP
        assert result[-1] == Terminal.CLIMAX


def _get_terminal_cost(dp: DPTable) -> float:
    from src.narrative_balancer.grammar.symbols import Terminal

    return dp.get_cost(Terminal.SETUP, 1)


# ---------------------------------------------------------------- arbitrator
class TestArbitratorPaths:
    def test_load_config_default_no_file(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        cfg = load_arbitrator_config()
        assert cfg.priority_order == ["grammar", "csp", "dsp"]

    def test_load_config_from_file(self, tmp_path: Path):
        cfg_file = tmp_path / "arb.yaml"
        cfg_file.write_text(
            "priority_order: [dsp, csp, grammar]\nvalidate_output: false\n",
            encoding="utf-8",
        )
        cfg = load_arbitrator_config(cfg_file)
        assert cfg.priority_order == ["dsp", "csp", "grammar"]
        assert cfg.validate_output is False

    def test_all_balancers_fail_fallback(self):
        config = ArbitratorConfig(enabled_balancers={"grammar": True, "csp": True, "dsp": True})
        balancer = GlobalNarrativeBalancer(config=config)

        class FailingAdapter:
            name = "fail"

            def balance(self, state):
                raise RuntimeError("boom")

        balancer.adapters = {"grammar": FailingAdapter()}
        beats = [_beat(i) for i in range(1, 5)]
        result = balancer.orchestrate(beats)
        assert result.is_valid is False
        assert len(result.balanced_beats) == 4

    def test_validate_method(self):
        config = ArbitratorConfig()
        balancer = GlobalNarrativeBalancer(config=config)
        beats = [_beat(i) for i in range(1, 5)]
        vr = balancer.validate(beats)
        assert vr is not None

    def test_disabled_balancer_skipped(self):
        config = ArbitratorConfig(enabled_balancers={"grammar": False, "csp": False, "dsp": False})
        balancer = GlobalNarrativeBalancer(config=config)
        beats = [_beat(i) for i in range(1, 5)]
        result = balancer.orchestrate(beats)
        assert result.is_valid is False

    def test_resolver_no_proposals(self):
        from src.narrative_balancer.arbitrator.resolver import PriorityResolver

        config = ArbitratorConfig()
        resolver = PriorityResolver(config)
        state = PlotState.from_beats([_beat(i) for i in range(1, 5)])
        results = {"grammar": BalancerResult(balancer_name="grammar", beats=[], success=True)}
        final, actions, conflicts = resolver.resolve(state, results)
        assert len(final) == 4
        assert actions == []
        assert conflicts == []
