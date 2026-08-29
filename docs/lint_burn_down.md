# Lint / Type バーンダウン目標

最終目標: 全リポジトリで `ruff` / `mypy --strict` をブロッキング化するため、エラー数を 0 にする。

## 現在値（計測日: 2026-08-29）

| 指標 | コマンド | 現在値 |
|------|----------|--------|
| ruff エラー総数 | `ruff check src/ tests/` | 1008 |
| mypy --strict エラー総数 | `mypy --config-file pyproject.toml src/` | 1769 |

## 目標閾値

| 指標 | ブロッキング化条件 |
|------|--------------------|
| `ruff check src/ tests/` | 0 エラー |
| `mypy --strict src/` | 0 エラー |

## 達成手順

1. 新規・変更ファイルのゲート（`format-check`, `lint-new`, `typecheck-new`）で追加負債を防止。
2. 既存負債をモジュール単位で地道に削減（型ヒント追加、インポート整理、未使用削除）。
3. 両指標が 0 になったら `.github/workflows/ci.yml` の `lint` / `typecheck` ジョブから
   `continue-on-error: true` を削除し、全量ブロッキング化する。

## 進捗記録

| 日付 | ruff | mypy |
|------|------|------|
| 2026-08-29 | 1008 | 1769 |
