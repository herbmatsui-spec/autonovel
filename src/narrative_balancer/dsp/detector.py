"""Midpoint sagging detector for narrative tension."""

from typing import List, Optional
import numpy as np
from src.narrative_balancer.dsp.models import DSPConfig, SagDetection
from src.narrative_balancer.dsp.spectral import spectral_flatness, low_freq_energy_ratio


def detect_sag_in_window(window: np.ndarray, cfg: DSPConfig) -> tuple[bool, float, float, str]:
    """Analyze a single window for sagging / lack of narrative momentum.

    Returns (is_sag, flatness, low_freq_ratio, reason).
    """
    if len(window) < 3:
        return False, 0.0, 0.0, "Window too short"

    variance = float(np.var(window))
    mean_val = float(np.mean(window))
    flatness = spectral_flatness(window)
    low_freq = low_freq_energy_ratio(window)

    # Condition 1: Low variance plateau (stagnant tension)
    if variance < 0.25 and mean_val <= 6.0:
        return True, flatness, low_freq, f"Low variance plateau (var={variance:.2f}, mean={mean_val:.2f})"

    # Condition 2: Flatness exceeds threshold and low-frequency dominance is high
    if flatness >= cfg.flatness_threshold and low_freq >= cfg.low_freq_ratio_threshold:
        return True, flatness, low_freq, f"High spectral flatness ({flatness:.2f}) and low-frequency dominance ({low_freq:.2f})"

    # Condition 3: Subdued mid-arc energy (prolonged dip in middle section)
    if mean_val < 4.5 and low_freq >= 0.70:
        return True, flatness, low_freq, f"Prolonged low-energy trough (mean={mean_val:.2f}, low_freq={low_freq:.2f})"

    return False, flatness, low_freq, "Normal dynamics"


def detect_sag(curve: np.ndarray, ep: int, cfg: DSPConfig) -> bool:
    """Evaluate whether sagging occurs around episode `ep` (0-based index)."""
    n = len(curve)
    if n < cfg.window_size:
        # Sequence shorter than window size: guard clause
        is_sag, _, _, _ = detect_sag_in_window(curve, cfg)
        return is_sag

    start = max(0, ep - cfg.window_size + 1)
    end = ep + 1
    window = curve[start:end]
    if len(window) < 3:
        return False

    is_sag, _, _, _ = detect_sag_in_window(window, cfg)
    return is_sag


def scan_sags(curve: np.ndarray, cfg: DSPConfig) -> List[SagDetection]:
    """Scan the entire sequence for sagging windows across narrative timeline."""
    detections: List[SagDetection] = []
    n = len(curve)
    if n < 4:
        return detections

    w = cfg.window_size
    # Slide across timeline
    for ep in range(w - 1, n):
        start = ep - w + 1
        end = ep + 1
        window = curve[start:end]

        is_sag, flatness, low_freq, reason = detect_sag_in_window(window, cfg)
        if is_sag:
            target_ep = start + w // 2  # Target intervention at center of sag window
            detections.append(SagDetection(
                start_episode=start + 1,  # 1-based index
                end_episode=end,          # 1-based index
                detected_episode=target_ep + 1,
                spectral_flatness=flatness,
                low_freq_ratio=low_freq,
                is_sag=True,
                reason=reason,
            ))

    return detections
