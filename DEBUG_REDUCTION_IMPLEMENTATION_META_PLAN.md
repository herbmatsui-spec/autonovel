# デバッグ時間短縮実装計画書 作成のためのメタ計画書

## 目的
バイブコーディングでのデバッグ時間短縮のための3戦略（型安全性・観測可能性・テスト自動化）を本プロジェクトに適用するための**詳細実装計画書**を作成するための計画

---

## 1. 現状分析フェーズ（実装計画書作成前の調査）

### 1.1 型安全性の現状把握
- [ ] `pyproject.toml` の mypy 設定確認（`ignore_missing_imports = true` の影響範囲）
- [ ] `tsconfig.json` の strict モード確認（現状 `strict: true` だが `noUncheckedIndexedAccess` 未設定）
- [ ] 主要モジュール（`src/services/*`, `src/agents/*`, `src/backend/*`）の型注釈カバレッジ測定
- [ ] Pydantic v2 モデルの型完全性確認（`schemas/config.py` 等）
- [ ] Zod/Valibot 等の実行時バリデーション導入有無確認

### 1.2 観測可能性の現状把握
- [ ] `config/logging_config.py` の JSON 構造化ログ確認
- [ ] `src/core/observability.py` の TraceContext/StructuredLogger 確認
- [ ] OpenTelemetry 導入状況確認（`pyproject.toml` に `opentelemetry-api/sdk` あり）
- [ ] `src/core/otel_setup.py` の実装確認（カバレッジ 0%）
- [ ] 分散トレーシング（trace_id 伝播）のフロントエンド・バックエンド間連携確認
- [ ] メトリクス（Prometheus）エンドポイント・ダッシュボード確認

### 1.3 テスト自動化の現状把握
- [ ] 既存テスト種別：Unit/Integration/E2E/Contract/Property の配分確認
- [ ] `TEST_COVERAGE_IMPLEMENTATION_PLAN.md` のフェーズ進捗確認
- [ ] Hypothesis 導入済み（`tests/property/` 存在）の活用範囲
- [ ] Pact 等の Contract Testing 導入有無
- [ ] Mutation Testing (Stryker/mutmut) 導入有無
- [ ] CI/CD でのカバレッジゲート（現状 `--cov-fail-under=35`）確認

---

## 2. 実装計画書の構成設計

### 2.1 章立て案
```
# デバッグ時間短縮 実装計画書
## 1. エグゼクティブサマリー
## 2. 現状ギャップ分析（測定値付き）
## 3. 戦略1: 型安全性最大化（コンパイル時検出率向上）
## 4. 戦略2: 観測可能性ファースト設計（本番同等可視性）
## 5. 戦略3: テストを仕様に昇格（Property/Contract/Mutation）
## 6. 統合マイルストーン・依存関係・クリティカルパス
## 7. リスク・対策・成功指標（KPI）
## 8. すぐ着手可能な Quick Wins
```

### 2.2 各戦略の詳細セクション構成
- **現状メトリクス**（数値で示す）
- **目標メトリクス**（定量的）
- **実装タスク**（WBS形式、優先度・工数・担当）
- **設定変更・コード変更の具体例**（diff形式で示す）
- **検証方法**（どう確認するか）
- **段階的導入ステップ**（破壊的変更を避ける移行パス）

---

## 3. 情報収集アクション（このメタ計画実行時に並行実施）

| アクション | ツール | 成果物 |
|-----------|--------|--------|
| mypy strict 化の影響範囲スキャン | `mypy --strict src 2>&1 \| head -100` | エラー件数・分類 |
| TypeScript strict 検査 | `npm run typecheck 2>&1` | エラー件数・分類 |
| 型注釈カバレッジ測定 | `mypy --strict --warn-unreachable --warn-redundant-casts src 2>&1 \| grep -c "error:"` | カバレッジ率 |
| OpenTelemetry 実装状況確認 | `cat src/core/otel_setup.py` | 実装内容 |
| 既存テスト分類集計 | `find tests -name "*.py" -exec grep -l "hypothesis\|@given" {} \;` | Property test 数 |
| カバレッジ詳細レポート生成 | `pytest --cov=src --cov-report=html` | htmlcov/index.html |

---

## 4. 実装計画書作成スケジュール

| タスク | 期間 | 依存 |
|--------|------|------|
| 現状分析・メトリクス収集 | 0.5日 | - |
| 戦略1（型安全性）詳細計画策定 | 0.5日 | 現状分析完了 |
| 戦略2（観測可能性）詳細計画策定 | 0.5日 | 現状分析完了 |
| 戦略3（テスト自動化）詳細計画策定 | 0.5日 | 現状分析完了 + 既存計画参照 |
| 統合・依存関係整理・KPI設定 | 0.5日 | 3戦略完了 |
| ドキュメント執筆・レビュー | 0.5日 | 全完了 |
| **合計** | **3日** | - |

---

## 5. 成果物

- `DEBUG_REDUCTION_IMPLEMENTATION_PLAN.md` — 詳細実装計画書（本番適用用）
- 付録: 設定ファイル diff 例集
- 付録: 段階的導入チェックリスト

---

## 6. 承認フロー

1. このメタ計画のレビュー・承認
2. 現状分析実行・数値確定
3. 詳細計画書ドラフト作成
4. 技術レビュー（アーキテクト・QAリード）
5. 最終版確定・実装着手

---

## 7. 即時着手アクション（承認待ちの間に可能）

- [ ] `pyproject.toml` の `[tool.mypy]` に `strict = true` 追加（テスト実行で影響確認）
- [ ] `tsconfig.json` に `"noUncheckedIndexedAccess": true` 追加
- [ ] `config/logging_config.py` の JSON フォーマッタに `trace_id` 以外の標準フィールド追加
- [ ] `vitest.config.ts` の coverage thresholds を 50→60 に引き上げ