# ブラインドピアレビュー改善 実装計画書
## #5 決定論的スクラブ → #3 完全性検証 → #4 汚染防止

### 実装方針
- **全24ステップ**を **2フェーズ** に分割
- 各ステップは単体テスト可能な最小単位
- 既存テストを壊さない（後方互換維持）

---

## フェーズ 1: コア機能強化（ステップ 1〜12）
### 目標: 決定論的ハッシュ + 完全性検証API を `BlindReviewGate` に追加

| Step | 作業内容 | ファイル | テスト |
|------|----------|----------|--------|
| 1 | `_canonical_json()` ユーティリティ関数追加 | `blind_review.py` | 単体 |
| 2 | `_hash_token()` を `deterministic` 引数対応に修正 | `blind_review.py` | 単体 |
| 3 | `ScrubMode` に `"deterministic_hash"` 追加 | `blind_review.py` | 単体 |
| 4 | `BlindReviewGate.__init__` に `deterministic: bool` 追加 | `blind_review.py` | 単体 |
| 5 | `_deep_scrub()` で `deterministic` フラグ使用 | `blind_review.py` | 単体 |
| 6 | **既存テスト全パス確認**（後方互換） | `test_blind_review.py` | 回帰 |
| 7 | `deterministic_hash` モード用テスト追加 | `test_blind_review.py` | 単体 |
| 8 | `IsolationSchema` データクラス新規作成 | `blind_review.py` | 単体 |
| 9 | `BlindReviewGate` に `schema` 属性・互換コンストラクタ追加 | `blind_review.py` | 単体 |
| 10 | `verify_isolation(payload)` メソッド実装 | `blind_review.py` | 単体 |
| 11 | `VerificationResult` / `IsolationViolation` データクラス追加 | `blind_review.py` | 単体 |
| 12 | 完全性検証テスト追加（マーカー残留・未スクラブ検知） | `test_blind_review.py` | 単体 |

**完了基準**: `BlindReviewGate` 単体で決定論的ハッシュ・完全性検証が動作し、既存11テスト＋新規テストが全パス

---

## フェーズ 2: 統合・汚染防止（ステップ 13〜24）
### 目標: EventBus/GachaService にラウンド分離を統合、汚染検知を実装

| Step | 作業内容 | ファイル | テスト |
|------|----------|----------|--------|
| 13 | `AgentEvent` に `round_id`, `metadata` フィールド追加 | `event_bus.py` | 単体 |
| 14 | `EventBus.publish_blind()` に `round_id` 引数追加・メタデータ埋め込み | `event_bus.py` | 単体 |
| 15 | `BlindReviewGate` に `current_round_id` 引数追加 | `blind_review.py` | 単体 |
| 16 | `_deep_scrub()` でクロスラウンドマーカー検知・再スクラブ実装 | `blind_review.py` | 単体 |
| 17 | 汚染検知テスト追加（他ラウンドマーカー混入拒否） | `test_blind_review.py` | 単体 |
| 18 | `GachaService._create_isolated_plan_payload()` にゲート引数追加 | `gacha_service.py` | 統合 |
| 19 | `GachaService._run_review_round()` プライベートメソッド新設 | `gacha_service.py` | 統合 |
| 20 | `generate_plans()` をラウンド0として `_run_review_round()` 呼び出しにリファクタ | `gacha_service.py` | 統合 |
| 21 | ラウンド実行時に `round_id` 生成・ゲート・イベント発行に伝播 | `gacha_service.py` | 統合 |
| 22 | `BLIND_REVIEW_ROUND_COMPLETED` イベントに `round_id` 含める | `gacha_service.py` | 統合 |
| 23 | 統合テスト `test_blind_gacha_flow.py` 更新・パス確認 | `test_blind_gacha_flow.py` | 統合 |
| 24 | プロパティベーステスト追加（Hypothesis・隔離保証） | `test_isolation_property.py` | 負荷 |

**完了基準**: 統合テスト全パス、クロスラウンド汚染が検知・防止される、プロパティベーステストで任意ペイロードでも隔離保証

---

## 依存関係グラフ

```
Phase 1 (独立実行可能)
├── Step 1-5: 決定論的ハッシュ基盤
├── Step 6: 回帰テスト
├── Step 7: 新モードテスト
├── Step 8-11: 完全性検証API
└── Step 12: 検証テスト

Phase 2 (Phase 1 完了後)
├── Step 13-14: EventBus 拡張
├── Step 15-17: ゲート汚染検知
├── Step 18-22: GachaService 統合
├── Step 23: 統合テスト
└── Step 24: プロパティベーステスト
```

---

## リスク・対策

| リスク | 影響 | 対策 |
|--------|------|------|
| `repr()` → `json.dumps()` 変更でハッシュ値変化 | 既存ハッシュ比較テストが落ちる | Step 6 で検知、Step 7 で新モードのみ検証 |
| `blocked_keys` 必須化で既存コード破壊 | `GachaService` 等が動かない | 互換コンストラクタ `from_legacy()` で段階移行 |
| `round_id` 必須化で EventBus 破壊 | 既存 `publish_blind()` 呼び出しエラー | デフォルト引数・オプション化で互換維持 |
| ネスト深いペイロードで再帰上限 | `_deep_scrub()` が `RecursionError` | `sys.setrecursionlimit` 或いは反復実装へ変更 |

---

## 実装順序の理由

1. **Phase 1 単体完結**: `BlindReviewGate` だけで完結 → デバッグ容易
2. **決定論的ハッシュ最優先**: 破壊的変更なし（オプトイン）、即効性高
3. **完全性検証で基盤固め**: #4 汚染防止の検証ツールとして先に必要
4. **Phase 2 で統合**: EventBus→Gate→Service の順で依存解決