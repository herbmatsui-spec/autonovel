"""Source contribution and quality metrics analysis for fusion layer."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.fusion.models import FusedVector


def analyze_source_contribution(fused_history: List[FusedVector]) -> Dict[str, Any]:
    """融合履歴からソース別採用率、矛盾発生率、信頼度分布などの統計を分析する"""
    if not fused_history:
        return {
            "total_episodes": 0,
            "total_values": 0,
            "adoption_counts": {},
            "adoption_rates": {},
            "conflict_stats": {"total_conflicts": 0, "conflict_rate": 0.0},
            "confidence_distribution": {"avg": 0.0, "min": 0.0, "max": 0.0},
        }

    total_values = 0
    adoption_counts: Dict[str, int] = {}
    confidences: List[float] = []
    total_conflicts = 0

    for fv in fused_history:
        total_conflicts += len(fv.conflicts)
        for fval in fv.values.values():
            total_values += 1
            src = fval.primary_source
            adoption_counts[src] = adoption_counts.get(src, 0) + 1
            confidences.append(fval.confidence)

    adoption_rates = {
        src: (cnt / total_values if total_values > 0 else 0.0)
        for src, cnt in adoption_counts.items()
    }

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    min_conf = min(confidences) if confidences else 0.0
    max_conf = max(confidences) if confidences else 0.0

    return {
        "total_episodes": len(fused_history),
        "total_values": total_values,
        "adoption_counts": adoption_counts,
        "adoption_rates": adoption_rates,
        "conflict_stats": {
            "total_conflicts": total_conflicts,
            "conflict_rate": (total_conflicts / total_values) if total_values > 0 else 0.0,
        },
        "confidence_distribution": {
            "avg": round(avg_conf, 4),
            "min": round(min_conf, 4),
            "max": round(max_conf, 4),
        },
    }


def save_analytics_report(stats: Dict[str, Any], output_path: Optional[str | Path] = None) -> Path:
    """分析結果を JSON レポートとして保存"""
    if output_path is None:
        today_str = datetime.now(timezone.utc).strftime("%Y%m%d")
        output_path = Path(f"logs/fusion_analytics_{today_str}.json")
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
    return p
