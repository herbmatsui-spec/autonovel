# 技術的負債一覧

最終更新: 2024-07-14

## TODO/FIXME/HACK コメント一覧

| # | ファイル | 行 | 内容 | 分類 | 優先度 | 対応方針 |
|---|----------|----|------|------|--------|----------|
| 1 | `src/infrastructure/api/api_client.py` | 9 | `# TODO: Move errors to src/shared/utils` | 実装 | 中 | エラークラスを `src/core/exceptions.py` に統合済み。今後は同ファイルへの追加は行わない |
| 2 | `src/backend/tasks.py` | 83 | `# エンジンもDI化を想定すべきだが、まずはエンジン内の呼び出しを維持` | 延期 | 低 | ステップ38-40でEngine分割時に検討 |
| 3 | `src/backend/engine.py` | 43 | `# GeminiApiClient は core/llm_gateway.py に移動・統合されました。` | 削除 | 高 | コメント削除済み確認 |
| 4 | `src/backend/engine.py` | 89 | `# 冗長な委譲メソッドを削除しました。` | 削除 | 高 | コメント削除済み確認 |
| 5 | `prompts/manager.py` | 224 | `# TODO: テンプレート化` | 延期 | 中 | Jinja2テンプレート化が適切。スケジュール参照 |
| 6 | `src/agents/plot.py` | 56 | `"""TODO: 第X話以降のプロット再構築機能の実装"""` | 実装 | 中 | ステップ20-22でPlotAgent実装時に検討 |
| 7 | `streamlit_app/app.py` | 72 | `# TODO: エラーハンドリングの移行` | 延期 | 中 | AppErrorHandler への移行を計画 |
| 8 | `scripts/generate_plot.py` | 273 | `# TODO: 既存のLLMクライアントと統合` | 実装 | 低 | モック実装の改良 |

## 分類サマリー

| 分類 | 件数 | 説明 |
|------|------|------|
| 削除 | 2 | 不要なコメント（既に実施済み） |
| 延期 | 3 | 後で対応（ステップ38-40、PlotAgent実装時など） |
| 実装 | 3 | 実際のコード対応が必要 |

## 対応ステータス

### 即時対応可能（30分以内）

- [x] `src/backend/engine.py` の古いコメント削除 - 確認要
- [ ] `prompts/manager.py` の `get_style_instruction` メソッドをダミーメソッドとして明示的にマーク

### 短期対応（ステップ20-40の間）

- [ ] `src/agents/plot.py` の `rebuild_hegemony_plot` メソッド実装計画作成
- [ ] `streamlit_app/app.py` のエラーハンドリング移行計画

### 中期対応（ステップ38以降）

- [ ] `src/backend/tasks.py` のDI化検討
- [ ] `scripts/generate_plot.py` のLLMクライアント統合

## 次のステップ

1. ステップ14: 緊急度の高いTODOの解決（1-5）を実施
2. ステップ15: 緊急度の高いTODOの解決（6-10）を実施
3. ステップ41-43: 各ファイルの詳細TODO抽出と解決
