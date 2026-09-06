"""レビューセッション・ラウンド管理エンティティ。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4
import hashlib
import json


@dataclass
class ReviewRound:
    """単一レビューラウンドの結果。"""
    round_number: int
    timestamp: datetime
    plan_scores: dict[str, float]  # plan_id -> score
    plan_critiques: dict[str, dict[str, Any]]  # plan_id -> critique
    gate_config_hash: str  # BlindReviewGate 設定のハッシュ（再現性検証用）
    converged: bool = False
    feedback_hash: str | None = None  # スクラブ済みフィードバックのハッシュ

    def score_delta(self, previous: "ReviewRound | None") -> dict[str, float]:
        """前回ラウンドからのスコア変化量を返す。"""
        if previous is None:
            return {pid: score for pid, score in self.plan_scores.items()}
        return {
            pid: self.plan_scores[pid] - previous.plan_scores.get(pid, 0.0)
            for pid in self.plan_scores
        }


@dataclass
class ReviewSession:
    """複数ラウンドにわたるブラインドレビューのセッション全体。"""
    session_id: str = field(default_factory=lambda: f"review_{uuid4().hex[:12]}")
    request_id: str = ""  # GachaRequest.request_id と対応
    rounds: list[ReviewRound] = field(default_factory=list)
    gate_forbidden_agents: list[str] = field(default_factory=list)
    gate_mode: str = "scrub"
    gate_blocked_keys: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    final_recommendation: str | None = None  # 推奨 plan_id
    status: str = "in_progress"  # in_progress, completed, failed

    def add_round(self, round_: ReviewRound) -> None:
        """ラウンドを追加し、更新日時をリフレッシュ。"""
        self.rounds.append(round_)
        self.updated_at = datetime.now()

    def latest_round(self) -> ReviewRound | None:
        """最新ラウンドを取得。"""
        return self.rounds[-1] if self.rounds else None

    def should_continue_review(
        self,
        max_rounds: int = 3,
        score_delta_threshold: float = 2.0,
        min_rounds: int = 1,
    ) -> bool:
        """追加ラウンドを実施すべきか判定。

        条件:
        - 最小ラウンド数未満なら継続
        - 最大ラウンド数到達なら停止
        - 全プランのスコア変化が閾値未満で2ラウンド連続なら停止（収束判定）
        """
        if len(self.rounds) < min_rounds:
            return True
        if len(self.rounds) >= max_rounds:
            return False

        # 直近2ラウンドの変化をチェック
        if len(self.rounds) >= 2:
            last = self.rounds[-1]
            prev = self.rounds[-2]
            deltas = last.score_delta(prev)
            if all(abs(d) < score_delta_threshold for d in deltas.values()):
                return False  # 収束とみなす
        return True

    def get_convergence_report(self) -> dict[str, Any]:
        """収束分析レポートを生成。"""
        if len(self.rounds) < 2:
            return {"status": "insufficient_data", "rounds": len(self.rounds)}

        report = {
            "total_rounds": len(self.rounds),
            "plan_trajectories": {},
            "converged": not self.should_continue_review(),
        }
        for i in range(1, len(self.rounds)):
            curr = self.rounds[i]
            prev = self.rounds[i - 1]
            for pid in curr.plan_scores:
                traj = report["plan_trajectories"].setdefault(pid, [])
                traj.append({
                    "round": curr.round_number,
                    "score": curr.plan_scores[pid],
                    "delta": curr.plan_scores[pid] - prev.plan_scores.get(pid, 0.0),
                })
        return report

    @staticmethod
    def _compute_gate_config_hash(
        forbidden_agents: list[str],
        mode: str,
        blocked_keys: list[str],
    ) -> str:
        """ゲート設定の決定論的ハッシュを計算。"""
        config = {
            "forbidden_agents": sorted(forbidden_agents),
            "mode": mode,
            "blocked_keys": sorted(blocked_keys),
        }
        h = hashlib.sha256()
        h.update(json.dumps(config, sort_keys=True, ensure_ascii=False).encode("utf-8"))
        return h.hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        """JSONシリアライズ用辞書に変換。"""
        return {
            "session_id": self.session_id,
            "request_id": self.request_id,
            "rounds": [
                {
                    "round_number": r.round_number,
                    "timestamp": r.timestamp.isoformat(),
                    "plan_scores": r.plan_scores,
                    "plan_critiques": r.plan_critiques,
                    "gate_config_hash": r.gate_config_hash,
                    "converged": r.converged,
                    "feedback_hash": r.feedback_hash,
                }
                for r in self.rounds
            ],
            "gate_forbidden_agents": self.gate_forbidden_agents,
            "gate_mode": self.gate_mode,
            "gate_blocked_keys": self.gate_blocked_keys,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "final_recommendation": self.final_recommendation,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewSession":
        """辞書から復元。"""
        session = cls(
            session_id=data["session_id"],
            request_id=data["request_id"],
            gate_forbidden_agents=data["gate_forbidden_agents"],
            gate_mode=data["gate_mode"],
            gate_blocked_keys=data["gate_blocked_keys"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            final_recommendation=data.get("final_recommendation"),
            status=data.get("status", "in_progress"),
        )
        session.rounds = [
            ReviewRound(
                round_number=r["round_number"],
                timestamp=datetime.fromisoformat(r["timestamp"]),
                plan_scores=r["plan_scores"],
                plan_critiques=r["plan_critiques"],
                gate_config_hash=r["gate_config_hash"],
                converged=r.get("converged", False),
                feedback_hash=r.get("feedback_hash"),
            )
            for r in data.get("rounds", [])
        ]
        return session