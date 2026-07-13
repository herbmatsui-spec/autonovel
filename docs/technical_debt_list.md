# 技術的負債一覧

| ファイル | 行 | 内容 | 分類 |
|----------|----|------|------|
| `src/infrastructure/api/api_client.py` | 9 | `# TODO: Move errors to src/shared/utils` | 実装 |
| `src/backend/tasks.py` | 83 | `# エンジンもDI化を想定すべきだが、まずはエンジン内の呼び出しを維持` | 延期 |
| `src/backend/engine.py` | 43 | `# GeminiApiClient は core/llm_gateway.py に移動・統合されました。` | 削除 |
| `src/backend/engine.py` | 89 | `# 冗長な移譲メソッドを削除しました。` | 削除 |
