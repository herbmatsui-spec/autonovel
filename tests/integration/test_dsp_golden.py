"""Golden master tests for DSP tension balancer."""

import json
from pathlib import Path
import pytest
from src.narrative_balancer.dsp.balancer import DSPTensionBalancer
from src.narrative_balancer.dsp.models import Beat


def test_golden_master_reproducibility():
    # Deterministic test input
    beats = [Beat(episode=i, tension=3.0 if 15 <= i <= 25 else 5.0) for i in range(1, 41)]
    balancer = DSPTensionBalancer()
    run1 = [b.tension for b in balancer.correct(beats)]
    run2 = [b.tension for b in balancer.correct(beats)]

    # Exactly identical output across runs
    assert run1 == run2
