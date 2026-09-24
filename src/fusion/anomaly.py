"""Anomaly detection and alerting for emotional vector fusion."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from src.fusion.alerts import ConflictAlerter
from src.fusion.config import FusionConfig, load_fusion_config
from src.fusion.models import FusedVector

logger = logging.getLogger("fusion.anomaly")


class AnomalyDetector:
    """融合プロセスの異常（矛盾急増、作者未記入、平均信頼度低下）を検知するクラス"""

    def __init__(
        self,
        config: Optional[FusionConfig] = None,
        alerter: Optional[ConflictAlerter] = None,
    ):
        self.config = config or load_fusion_config()
        self.alerter = alerter or ConflictAlerter(self.config)

    def check_anomalies(
        self,
        current_fused: FusedVector,
        prev_fused: Optional[FusedVector] = None,
        recent_contributing_sources: Optional[List[List[str]]] = None,
    ) -> List[Dict[str, Any]]:
        """現在の FusedVector と履歴から異常を検出し、異常アラートのリストを返す"""
        anomalies: List[Dict[str, Any]] = []
        thresh = self.config.anomaly_thresholds

        # 1. 矛盾急増 (conflict_spike)
        curr_conflicts = len(current_fused.conflicts)
        if prev_fused is not None:
            prev_conflicts = len(prev_fused.conflicts)
            if prev_conflicts > 0 and (curr_conflicts / prev_conflicts) >= thresh.conflict_spike:
                anomalies.append({
                    "type": "CONFLICT_SPIKE",
                    "message": f"Conflict count spiked from {prev_conflicts} to {curr_conflicts} (ratio: {curr_conflicts / prev_conflicts:.2f})",
                    "severity": "HIGH",
                    "curr_conflicts": curr_conflicts,
                    "prev_conflicts": prev_conflicts,
                })
        elif curr_conflicts >= 5:
            # 初回または前話なしで矛盾が多数ある場合
            anomalies.append({
                "type": "CONFLICT_SPIKE",
                "message": f"Initial high conflict count detected: {curr_conflicts}",
                "severity": "MEDIUM",
                "curr_conflicts": curr_conflicts,
            })

        # 2. 特定ソース (annotation) が3話連続未更新
        if recent_contributing_sources is not None:
            stale_limit = thresh.annotation_stale_episodes
            if len(recent_contributing_sources) >= stale_limit:
                # 直近stale_limit話で 'annotation' が一度も含まれていないか確認
                recent_window = recent_contributing_sources[-stale_limit:]
                has_annotation = any("annotation" in srcs for srcs in recent_window)
                if not has_annotation:
                    anomalies.append({
                        "type": "ANNOTATION_STALE",
                        "message": f"Annotation source has not been updated for {stale_limit} consecutive episodes.",
                        "severity": "MEDIUM",
                        "stale_episodes": stale_limit,
                    })

        # 3. 融合信頼度平均が閾値 (0.6) 未満
        if current_fused.values:
            avg_conf = sum(v.confidence for v in current_fused.values.values()) / len(current_fused.values)
            if avg_conf < thresh.min_avg_confidence:
                anomalies.append({
                    "type": "LOW_AVG_CONFIDENCE",
                    "message": f"Average fusion confidence ({avg_conf:.2f}) dropped below threshold ({thresh.min_avg_confidence}).",
                    "severity": "HIGH",
                    "avg_confidence": round(avg_conf, 4),
                    "threshold": thresh.min_avg_confidence,
                })

        for anomaly in anomalies:
            logger.warning(f"[AnomalyDetected] {anomaly['type']}: {anomaly['message']}")

        return anomalies
