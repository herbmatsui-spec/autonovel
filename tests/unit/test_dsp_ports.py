"""Unit tests for DSP ports."""

from src.narrative_balancer.dsp.ports import TensionAnalyzer, Corrector
from src.narrative_balancer.dsp.balancer import DSPTensionBalancer


def test_dsp_balancer_implements_ports():
    balancer = DSPTensionBalancer()
    assert isinstance(balancer, TensionAnalyzer)
    assert isinstance(balancer, Corrector)
