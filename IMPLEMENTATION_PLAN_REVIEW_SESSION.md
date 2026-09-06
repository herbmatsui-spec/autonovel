# ブラインドピアレビュー セッション管理 実装計画書

## 概要
複数ラウンドのブラインドピアレビューをサポートするため、レビューセッションの状態管理と永続化機能を実装する。

---

## 1. ドメインモデル追加

### 1.1 新規ファイル: `src/domain/entities/review_session.py`

```python
"""レビューセッション・ラウンド管理エンティティ。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from src.domain.entities.easy_mode import GachaPlan, GachaPlanType


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
```

### 1.2 `src/domain/entities/easy_mode.py` への追加

`GachaRequest` に `review_session_id` フィールドを追加（オプショナル）。

---

## 2. データベーススキーマ拡張

### 2.1 `EasyModeDraft` モデル拡張 (`src/backend/database/models.py`)

既存テーブルにカラム追加（マイグレーション対応）:
- `review_session_json` (Text, nullable) - ReviewSession.to_dict() の JSON
- `kind` に `"review_session"` を追加許可

### 2.2 マイグレーションスクリプト

Alembic または手動 SQL で `ALTER TABLE easy_mode_drafts ADD COLUMN review_session_json TEXT;`

---

## 3. リポジトリ拡張

### 3.1 `EasyModeDraftRepository` にメソッド追加

```python
@retry_on_lock()
async def save_review_session(self, session: ReviewSession) -> None:
    """ReviewSession を永続化。"""
    draft = EasyModeDraft(
        draft_id=session.session_id,
        kind="review_session",
        payload_json=json.dumps(session.to_dict(), ensure_ascii=False),
        parent_draft_id=session.request_id,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )
    self.session.add(draft)

async def load_review_session(self, session_id: str) -> ReviewSession | None:
    """ReviewSession を読み込み。"""
    result = await self.session.execute(
        select(EasyModeDraft).where(
            EasyModeDraft.draft_id == session_id,
            EasyModeDraft.kind == "review_session",
        )
    )
    draft = result.scalar_one_or_none()
    if draft is None:
        return None
    return ReviewSession.from_dict(json.loads(draft.payload_json))

async def load_review_session_by_request(self, request_id: str) -> ReviewSession | None:
    """request_id から最新の ReviewSession を読み込み。"""
    result = await self.session.execute(
        select(EasyModeDraft).where(
            EasyModeDraft.parent_draft_id == request_id,
            EasyModeDraft.kind == "review_session",
        ).order_by(EasyModeDraft.created_at.desc())
    )
    draft = result.scalars().first()
    if draft is None:
        return None
    return ReviewSession.from_dict(json.loads(draft.payload_json))
```

---

## 4. GachaService 統合

### 4.1 `generate_plans()` の改修

1. 開始時に `ReviewSession` を新規作成（または `review_session_id` 指定時はロード）
2. 既存の評価ループを「ラウンド0」として `ReviewRound` に記録
3. `session.add_round(round_)` で追加
4. `should_continue_review()` で継続判定（現状は1ラウンドで停止）
5. セッションをリポジトリで保存
6. `GachaResponse` に `review_session_id` を含める（フィールド追加）

### 4.2 将来の拡張ポイント

- `_run_additional_review_round()` プライベートメソッドを用意
- 外部から `continue_review(session_id)` で再開可能に

---

## 5. イベント発行拡張

### 5.1 `EventBus` イベントタイプ追加

```python
BLIND_REVIEW_ROUND_COMPLETED = "blind_review.round_completed"
BLIND_REVIEW_SESSION_COMPLETED = "blind_review.session_completed"
```

### 5.2 `publish_blind()` 後、ラウンド完了イベントを発行

---

## 6. テスト計画

### 6.1 単体テスト (`tests/unit/test_review_session.py`)
- `ReviewSession.should_continue_review()` の境界値テスト
- `get_convergence_report()` の正確性
- シリアライズ/デシリアライズのラウンドトリップ

### 6.2 統合テスト (`tests/integration/test_review_session_flow.py`)
- GachaService.generate_plans() が ReviewSession を作成・保存すること
- リポジトリから正しく復元できること
- 同一 request_id で再開可能なこと

---

## 7. 実装順序

| 順序 | タスク | ファイル | 優先度 |
|------|--------|----------|--------|
| 1 | ReviewSession/ReviewRound エンティティ作成 | `src/domain/entities/review_session.py` | P0 |
| 2 | easy_mode.py に review_session_id 追加 | `src/domain/entities/easy_mode.py` | P0 |
| 3 | EasyModeDraft モデルにカラム追加 | `src/backend/database/models.py` | P0 |
| 4 | マイグレーション実行 | SQL/Alembic | P0 |
| 5 | リポジトリメソッド追加 | `easy_mode_draft_repository.py` | P0 |
| 6 | GachaService 統合 | `gacha_service.py` | P0 |
| 7 | イベントタイプ追加・発行 | `event_bus.py` | P1 |
| 8 | 単体テスト作成 | `test_review_session.py` | P1 |
| 9 | 統合テスト作成 | `test_review_session_flow.py` | P1 |

---

## 8. 互換性・リスク

- **既存データ互換**: 新カラムは nullable。既存レコードは `review_session_json=NULL` で正常動作
- **API 互換**: `GachaRequest.review_session_id` は Optional。未指定時は新規セッション作成
- **パフォーマンス**: JSON カラムへの保存は既存 `payload_json` と同等。インデックス不要（親 draft_id で検索）
- **ロールバック**: カラム削除のみで元に戻せる

---

## 9. 完了基準

- [ ] `ReviewSession` エンティティが単体テストで全パス
- [ ] `GachaService.generate_plans()` 実行後に `review_session` レコードがDBに作成される
- [ ] 同一 `request_id` で `load_review_session_by_request()` が最新セッションを返す
- [ ] `should_continue_review()` が正しく収束判定する
- [ ] 統合テスト `test_blind_gacha_flow.py` が既存機能を壊さずパス