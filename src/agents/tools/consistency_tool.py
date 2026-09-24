"""Emotional consistency checker comparing CoreMemory with baseline FusedVector."""
from __future__ import annotations

from typing import Any, Dict, List
from src.agents.memory.core_memory import CoreMemory
from src.fusion.models import FusedVector
from src.pipeline.emotional_residue import EmotionType


def check_emotional_consistency(
    core_memory: CoreMemory,
    baseline_fused: FusedVector,
    divergence_threshold: float = 0.5,
) -> Dict[str, Any]:
    """現在 CoreMemory の感情値と直前話 baseline FusedVector を比較し、不整合を検出する"""
    warnings: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []

    # baseline の全感情値を参照
    for (src, tgt, emo), fval in baseline_fused.values.items():
        pair_key = f"{src}->{tgt}"
        emo_str = emo.value if hasattr(emo, "value") else str(emo)

        core_emotions = core_memory.character_emotions.get(pair_key, {})
        if emo_str not in core_emotions:
            continue

        core_val = float(core_emotions[emo_str])
        base_val = float(fval.value)

        diff = abs(core_val - base_val)

        # 1. 符号反転（矛盾）
        if (core_val > 0.2 and base_val < -0.2) or (core_val < -0.2 and base_val > 0.2):
            errors.append({
                "pair": (src, tgt),
                "emotion": emo_str,
                "core_value": core_val,
                "baseline_value": base_val,
                "type": "SIGN_FLIP_CONFLICT",
                "message": f"感情の極性が急反転しています: baseline={base_val} vs core={core_val}",
            })
        # 2. 大きな乖離
        elif diff >= divergence_threshold:
            warnings.append({
                "pair": (src, tgt),
                "emotion": emo_str,
                "core_value": core_val,
                "baseline_value": base_val,
                "diff": round(diff, 4),
                "type": "LARGE_DIVERGENCE",
                "message": f"感情値の乖離が閾値({divergence_threshold})を超えています (差: {diff:.2f})",
            })

    return {
        "consistent": len(errors) == 0,
        "warnings_count": len(warnings),
        "errors_count": len(errors),
        "warnings": warnings,
        "errors": errors,
    }


__all__ = ["check_emotional_consistency"]
