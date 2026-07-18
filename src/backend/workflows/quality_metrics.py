"""
エピソード品質メトリクスの収集と分析

WritingGraphManager の Actor-Critic ループで生成された各エピソードの
整合性 / 因果性 / ドッグフィード結果を記録し、ジャンル別の品質トレンドを
提供する。低性能 LLM でもオーバーヘッドが小さくなるようシンプルに保つ。
"""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class QualityMetrics:
    ep_num: int
    integrity_ok: bool
    causal_ok: bool
    rate: float
    ac_iter: int
    threshold: int
    timestamp: float
    genre: Optional[str] = None
    dogfeed_ok: bool = True
    causal_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ep_num": self.ep_num,
            "integrity_ok": self.integrity_ok,
            "causal_ok": self.causal_ok,
            "rate": self.rate,
            "ac_iter": self.ac_iter,
            "threshold": self.threshold,
            "timestamp": self.timestamp,
            "genre": self.genre,
            "dogfeed_ok": self.dogfeed_ok,
            "causal_reason": self.causal_reason,
        }

    @property
    def overall_quality(self) -> float:
        """総合品質スコア (0.0-1.0)"""
        score = 0.0
        if self.integrity_ok:
            score += 0.4
        if self.causal_ok:
            score += 0.3
        if self.dogfeed_ok:
            score += 0.2
        score += self.rate * 0.1
        return min(score, 1.0)


class QualityMetricsCollector:
    """エピソード品質を蓄積し、ジャンル別のベースラインを更新する"""

    def __init__(self):
        self.episode_metrics: Dict[int, QualityMetrics] = {}
        self.genre_baselines: Dict[str, Dict[str, float]] = {}

    def record(self, metrics: QualityMetrics) -> None:
        self.episode_metrics[metrics.ep_num] = metrics
        if metrics.genre:
            self._update_genre_baseline(metrics)

    def get(self, ep_num: int) -> Optional[QualityMetrics]:
        return self.episode_metrics.get(ep_num)

    def _update_genre_baseline(self, metrics: QualityMetrics) -> None:
        genre = metrics.genre
        if genre not in self.genre_baselines:
            self.genre_baselines[genre] = {
                "integrity_rate": 0.0,
                "causal_rate": 0.0,
                "avg_rate": 0.0,
                "count": 0,
            }
        baseline = self.genre_baselines[genre]
        count = baseline["count"]
        baseline["integrity_rate"] = (baseline["integrity_rate"] * count + (1.0 if metrics.integrity_ok else 0.0)) / (count + 1)
        baseline["causal_rate"] = (baseline["causal_rate"] * count + (1.0 if metrics.causal_ok else 0.0)) / (count + 1)
        baseline["avg_rate"] = (baseline["avg_rate"] * count + metrics.rate) / (count + 1)
        baseline["count"] = count + 1

    def get_quality_trend(self, genre: Optional[str] = None) -> Dict[str, float]:
        if genre and genre in self.genre_baselines:
            return self.genre_baselines[genre]
        all_metrics = list(self.episode_metrics.values())
        if not all_metrics:
            return {"integrity_rate": 0.0, "causal_rate": 0.0, "avg_rate": 0.0, "count": 0}
        total = len(all_metrics)
        integrity = sum(1 for m in all_metrics if m.integrity_ok) / total
        causal = sum(1 for m in all_metrics if m.causal_ok) / total
        avg_rate = sum(m.rate for m in all_metrics) / total
        return {
            "integrity_rate": integrity,
            "causal_rate": causal,
            "avg_rate": avg_rate,
            "count": total,
        }
