"""Main DSP Narrative Tension Balancer implementation."""

import json
import logging
import time
from typing import List, Optional, Set
import numpy as np

from src.narrative_balancer.dsp.models import (
    Beat,
    CorrectionAction,
    DSPConfig,
    SagDetection,
)
from src.narrative_balancer.dsp.ports import TensionAnalyzer, Corrector
from src.narrative_balancer.dsp.signal import extract_tension_curve
from src.narrative_balancer.dsp.detector import scan_sags
from src.narrative_balancer.dsp.impulse import design_midpoint_disaster_impulse
from src.narrative_balancer.dsp.corrector import apply_impulse_correction, writeback_corrected_beats

logger = logging.getLogger(__name__)


class DSPTensionBalancer(TensionAnalyzer, Corrector):
    """Discrete Signal Processing based story tension balancer."""

    def __init__(self, config: Optional[DSPConfig] = None, log_jsonl: bool = True):
        self.config = config or DSPConfig()
        self.log_jsonl = log_jsonl
        self.execution_logs: List[dict] = []

    def analyze(self, beats: List[Beat]) -> List[SagDetection]:
        """Analyze beat sheet tension signal for sagging sections."""
        if not beats:
            return []

        curve = extract_tension_curve(beats)
        return scan_sags(curve, self.config)

    def correct(self, beats: List[Beat]) -> List[Beat]:
        """Detect tension sags and apply impulse corrections."""
        if not beats:
            return []

        start_time = time.perf_counter()
        original_curve = extract_tension_curve(beats)
        current_curve = original_curve.copy()

        sags = self.analyze(beats)
        corrected_eps: Set[int] = set()

        impulse = design_midpoint_disaster_impulse(
            length=self.config.impulse.length,
            peak=self.config.impulse.peak,
            decay=self.config.impulse.decay,
        )

        applied_actions: List[CorrectionAction] = []

        for sag in sags:
            target_0idx = sag.detected_episode - 1
            if target_0idx < 0 or target_0idx >= len(current_curve):
                continue

            # Check if this region already received an impulse intervention
            if any((target_0idx <= (ep - 1) < target_0idx + len(impulse)) for ep in corrected_eps):
                continue

            current_curve = apply_impulse_correction(
                current_curve,
                target_0idx,
                impulse,
                min_clip=self.config.min_tension_clip,
                max_clip=self.config.max_tension_clip,
            )

            # Mark corrected episodes (1-based)
            for offset in range(min(len(impulse), len(current_curve) - target_0idx)):
                ep_1based = target_0idx + offset + 1
                corrected_eps.add(ep_1based)
                applied_actions.append(CorrectionAction(
                    episode=ep_1based,
                    action_type="IMPULSE_TENSION_BOOST",
                    target_field="tension",
                    original_value=round(float(original_curve[ep_1based - 1]), 2),
                    new_value=round(float(current_curve[ep_1based - 1]), 2),
                    reason=f"Sag detected between Ep {sag.start_episode}-{sag.end_episode}: {sag.reason}",
                ))

        corrected_beats = writeback_corrected_beats(beats, current_curve, corrected_eps)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # Structured logging
        log_record = {
            "timestamp": time.time(),
            "total_episodes": len(beats),
            "sags_detected": len(sags),
            "corrected_episodes_count": len(corrected_eps),
            "elapsed_ms": round(elapsed_ms, 3),
            "actions": [a.model_dump() for a in applied_actions],
        }
        self.execution_logs.append(log_record)
        if self.log_jsonl:
            logger.info("DSP_BALANCER_METRIC: %s", json.dumps(log_record, ensure_ascii=False))

        return corrected_beats
