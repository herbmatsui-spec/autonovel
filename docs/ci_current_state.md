# CI の現在状態（調査メモ）

対象ファイル: `.github/workflows/ci.yml`

## ジョブ一覧

| ジョブ名 | 目的 | ブロッキング? | 備考 |
|----------|------|---------------|------|
| `lint` | 全 `src/`, `tests/` の ruff チェック + 統計出力 | 非ブロッキング (`continue-on-error: true`) | 負債トラッカーとして機能 |
| `typecheck` | 全 `src/` の `mypy --config-file pyproject.toml` | 非ブロッキング (`continue-on-error: true`) | 同様に負債トラッカー |
| `changed-files` | PR/_push で変更された Python ファイル一覧を算出 | - | 他ジョブへの入力 |
| `format-check` | 変更ファイルのみ `ruff format --check` | **ブロッキング** (`needs: [changed-files]`) | 新規コードのフォーマット違反で失敗 |
| `lint-new` | 変更ファイルのみ `ruff check` | **ブロッキング** | 新規コードの lint 違反で失敗 |
| `unit-test` | `tests/unit` をカバレッジ付きで実行 | `needs: [format-check, lint-new]` のため間接的にブロッキング |  |
| `integration-test` | `tests/integration` + ベクタストアを実行（chroma/redis サービス付き） | 同上 |  |
| `continuity-check` | `novel_50ep` の連続性テスト | 同上 |  |

## 重要な事実

- **新規・変更ファイルに対する ruff のブロッキングゲートはすでに存在**（`format-check`, `lint-new`）。
- **mypy のブロッキングゲートは存在しない**（全量ともに `continue-on-error`）。
- 全リポジトリに対する ruff/mypy のブロッキング化は、負債（ruff 約1008件, mypy 約1769件）が 0 になるまで意図的に保留されている。

## 次アクション

1. 新規ファイル向けの `mypy --strict` ブロッキングジョブ（`typecheck-new`）を追加する（計画ステップ 3）。
2. 全量ブロッキング化の閾値と手順を `docs/lint_burn_down.md` に定義する（計画ステップ 4）。
