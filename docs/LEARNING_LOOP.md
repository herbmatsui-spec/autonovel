# ネガティブサンプル蓄積・監査精度向上の仕組み

## 概要

本ドキュメントでは、ユーザーのレビュー判断（承認/却下/修正）から学習データを自動生成し、将来の監査精度を向上させる**学習ループ**の仕組みを解説します。

---

## 学習ループ全体図

```
┌─────────────────────────────────────────────────────────────────┐
│                        学習ループ                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    監査実行     ┌──────────┐    レビュー要求    │
│  │  監査    │ ─────────────► │ Patch    │ ─────────────────► │
│  │  エージェント    │   失敗       │ Review   │                   │
│  └──────────┘              └────┬─────┘                   │
│                                 │                          │
│                    ┌────────────┼────────────┐             │
│                    ▼            ▼            ▼             │
│             ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│             │  承認    │  │  却下    │  │  修正    │       │
│             │ (Positive)│  │(Negative)│  │(Positive)│       │
│             └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│                  │             │             │              │
│                  ▼             ▼             ▼              │
│         ┌──────────────────────────────────────────┐        │
│         │        学習データサービス                  │        │
│         │  - ベクトルDB保存 (ChromaDB)             │        │
│         │  - ラベル付け: positive / negative       │        │
│         │  - パターン統計更新                       │        │
│         └────────────────────┬─────────────────────┘        │
│                              │                               │
│                              ▼                               │
│         ┌──────────────────────────────────────────┐        │
│         │        次回監査時の動的調整               │        │
│         │  - 同タイプのネガティブ多い → 閾値緩和     │        │
│         │  - 同タイプのポジティブ多い → 信頼度向上   │        │
│         │  - 完全スキップ判定も可能                │        │
│         └──────────────────────────────────────────┘        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## データ構造

### 学習サンプル（ChromaDB に保存）

コレクション: `audit_learning_samples`

```json
{
  "document": "audit_type:logical_consistency feedback:{...} label:negative",
  "metadata": {
    "patch_review_id": 42,
    "audit_type": "logical_consistency",
    "label": "negative",
    "resolution": "rejected",
    "reviewer_id": "editor1",
    "created_at": "2026-01-15T10:30:00"
  },
  "id": "hash..."
}
```

### PatchReview.learning_metadata（累積統計）

```json
{
  "negative_sample_candidates": ["logical_consistency", "causal_integrity"],
  "learning_adjusted": ["logical_consistency"],
  "learned_patterns": [
    {
      "audit_type": "logical_consistency",
      "label": "negative",
      "resolution": "rejected",
      "timestamp": "2026-01-15T10:30:00"
    },
    {
      "audit_type": "logical_consistency",
      "label": "positive",
      "resolution": "approved",
      "timestamp": "2026-01-16T14:00:00"
    }
  ]
}
```

---

## ラベリングルール

| ユーザーアクション | ラベル | 学習への影響 |
|------------------|--------|-------------|
| **却下** | `negative` | 「この指摘は誤り」→ 同パターンの検出を抑制/閾値緩和 |
| **承認** | `positive` | 「この指摘は正しい」→ 同パターンの信頼度向上 |
| **修正案提示** | `positive` | 「方向性は合ってるが値が違う」→ 正例として蓄積 |

> **重要**: `modified`（修正）は `positive` 扱いです。ユーザーが「指摘自体は妥当だが推奨値が違う」と判断したことを意味するためです。

---

## 動的閾値調整アルゴリズム

### `should_skip_audit_type()` の判定ロジック

```python
async def should_skip_audit_type(self, audit_type: str) -> tuple[bool, float]:
    negative_count = count_negative_samples(audit_type)
    positive_count = count_positive_samples(audit_type)

    # 条件1: ネガティブが圧倒的多数 & 十分なサンプル数
    if negative_count > positive_count * 3 and negative_count >= 5:
        return True, -0.3   # 完全スキップ推奨、信頼度-0.3

    # 条件2: ネガティブ優勢 & ある程度のサンプル数
    if negative_count > positive_count and negative_count >= 3:
        return False, -0.15 # スキップせず信頼度のみ下げる

    # 条件3: データ不足またはポジティブ優勢
    return False, 0.0       # 調整なし
```

### 監査側での適用（AuditAgent）

```python
# 監査失敗検出時
should_downgrade, conf_adj = await self._check_learning_adjustment("logical_consistency")

if should_downgrade:
    # この監査失敗を warning 扱いに格下げ
    # → PatchReview 作成時 severity を high → medium に下げる
    # → auto-retry しないが、レビュー待ちにはする
    severity = "medium"
    learning_adjusted = True
else:
    # 通常通り処理
    pass
```

---

## 監査タイプ別の学習効果

| 監査タイプ | 典型的な誤検知パターン | 学習効果の現れ方 |
|------------|----------------------|------------------|
| `logical_consistency` | 「設定上は不可能だが、主人公のチート能力で可能」 | チート設定を考慮し直すよう閾値緩和 |
| `causal_integrity` | 「伏線回収が後話まである」→ 因果律違反と誤判定 | 長期伏線を許容するよう調整 |
| `ability_consistency` | 「成長イベントで能力値変動」→ 不整合と誤判定 | 成長許容範囲を学習 |
| `deai` | 「意図的な定型文・テンプレート使用」 | 文体の許容幅を広げる |
| `fast_screen` | 「非標準的だが面白いプロット構成」 | 構成の多様性を許容 |

---

## ダッシュボード指標（将来実装）

### 精度メトリクス

| 指標 | 計算式 | 目安 |
|------|--------|------|
| **精度** | TP / (TP + FP) | 0.85 以上 |
| **再現率** | TP / (TP + FN) | 0.80 以上 |
| **F1スコア** | 2 * P * R / (P + R) | 0.82 以上 |
| **ネガティブサンプル率** | Neg / (Pos + Neg) | 0.3 以下 |

*TP: 承認された指摘, FP: 却下された指摘, FN: 見逃された矛盾（ユーザー後発見）*

### 監視すべきシグナル

- **ネガティブサンプル急増**: 監査プロンプト/閾値に根本的問題あり
- **特定タイプのみネガティブ多発**: その監査ロジックの見直し必要
- **学習調整発動率上昇**: システムが「学習モード」に入っている（正常）

---

## API

### ネガティブパターン検索
```bash
GET /api/learning/negative-patterns?audit_type=logical_consistency&limit=10
```

### ポジティブパターン検索
```bash
GET /api/learning/positive-patterns?audit_type=causal_integrity&limit=10
```

### 精度統計取得
```bash
GET /api/learning/stats?book_id=1
```

### 学習データ記録（内部API）
```bash
POST /api/learning/record
Body: { "patch_review_id": 42, "resolution": "rejected", "reviewer_id": "editor1" }
```

---

## 運用ガイド

### 1. 初期学習期間（最初の 50-100 話）

- 積極的にレビューを行い、学習データを蓄積
- 却下理由に「意図的」「チート設定」「伏線」等のキーワードを含めると後で分析しやすい
- 最初は調整が発動しにくい（サンプル数不足のため）→ 正常

### 2. 安定期以降

- 学習調整が発動し始める（ログに `Learning-adjusted audits` が出る）
- 誤検知が減り、レビュー負荷が低下
- 定期的に `stats` API で精度推移を確認

### 3. ジャンル/エンジン変更時

- 学習データは `book_id` 単位で蓄積されるため、新作ではゼロから開始
- 同ジャンルの過去作データを転用する機能は将来実装予定

---

## トラブルシューティング

| 現象 | 原因 | 対処 |
|------|------|------|
| 学習調整が発動しない | サンプル数不足（5件未満） | レビューを継続、データ蓄積待ち |
| 正しい指摘までスキップされる | ネガティブサンプルにノイズ混入 | `is_quality_related` フラグでフィルタ、明らかな誤却下を除外 |
| ChromaDB 検索が遅い | インデックス未作成/データ量過大 | 古いサンプルのアーカイブ、コレクション再構築 |
| 統計が合わない | `learning_metadata` 更新漏れ | `record_negative_sample` 呼び出し確認、トランザクション整合性確認 |

---

## 将来の拡張

1. **Few-shot プロンプト最適化**: 蓄積した正例を監査プロンプトの few-shot 例として自動注入
2. **Fine-tuning**: 十分なデータ蓄積後、監査用軽量モデルをファインチューニング
3. **クロスブック学習**: 同ジャンル・同エンジンの複数作品間で学習データ共有
4. **説明可能AI**: なぜこの指摘をしたか/しなかったかの理由を自然言語で生成
5. **アクティブラーニング**: 不確実性が高いサンプルを優先的にユーザーに提示