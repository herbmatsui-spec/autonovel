# テストカバレッジ向上 実装計画書

## 概要
既存機能を変更せず、以下3領域のテストカバレッジを向上させるための24ステップ計画。

1. 設定バリデーター（ConfigValidator）のエッジケーステスト
2. 書記エージェントおよびコンポーネントの単体テスト
3. APIエンドポイントの統合テスト

---

## フェーズ1: 設定バリデーターのエッジケーステスト（ステップ 1-8）

### ステップ 1: テストファイル作成
`tests/unit/test_config_validator_edges.py` を新規作成。`ConfigValidator` のインポートと基本フィクスチャを定義。

### ステップ 2: 不正TOMLファイルのテスト
`config/settings.toml` を一時的に不正な構文（例: 未閉じの括弧）に書き換え、`load_settings_toml` が `tomllib.TOMLDecodeError` を投げることを確認。

### ステップ 3: 必須フィールド欠如のテスト
`model_writing` など必須フィールドを削除した TOML を作成し、バリデーションエラー（`ValidationError`）が発生することを確認。

### ステップ 4: 型不正フィールドのテスト
`max_concurrency` に文字列 `"five"` を指定した TOML を作成し、型変換エラーが適切に処理されることを確認。

### ステップ 5: 環境変数オーバーライド（正常系）テスト
`KAKU_MODEL_WRITING=custom-model` を `os.environ` に設定し、`apply_env_overrides` 後に設定値が上書きされることを確認。

### ステップ 6: 環境変数オーバーライド（不正値）テスト
`KAKU_MAX_CONCURRENCY=invalid` を設定し、型変換失敗時の挙動（例外 or デフォルト値）を確認・文書化。

### ステップ 7: マージ優先順位のテスト
`settings.toml` と `models.yaml` の両方に `model_planning` がある場合、TOML が優先されることを確認（`validate_all` のマージロジック）。

### ステップ 8: ドメインプロファイル読み込み失敗のテスト
`config/domain_profiles/` に不正な JSON を配置し、`validate_all(strict=False)` でデフォルト値で代替されることを確認。

---

## フェーズ2: 書記エージェント・コンポーネントの単体テスト（ステップ 9-16）

### ステップ 9: テストモジュール作成
`tests/unit/agents/test_writing_components.py` を新規作成。`EpisodeWriter`, `RewriteOrchestrator`, `BibleExtractor` をインポート。

### ステップ 10: EpisodeWriter.write() の正常系テスト
- `llm.generate_text` をモックし、固定文字列を返すように設定
- `context_builder.build` をモックし、ダミーのコンテキスト辞書を返す
- 生成されたテキストが期待通りの長さ・内容か検証

### ステップ 11: EpisodeWriter.write() の例外系テスト
- `llm.generate_text` が `RuntimeError` を投げるようにモック
- 例外が適切にログ出力され、空文字またはエラー結果が返ることを確認

### ステップ 12: RewriteOrchestrator.run() のリライト回数テスト
- `auditor.audit` をモックし、初回は "Major"、2回目は "Minor" を返すように設定
- `max_iterations=2` で 2 回リライトが実行されることを確認

### ステップ 13: RewriteOrchestrator.run() の早期終了テスト
- `auditor.audit` が初回から "OK" を返すようにモック
- リライトが 0 回で終了することを確認

### ステップ 14: BibleExtractor.extract() の正常系テスト
- `llm.generate_json` をモックし、既知の構造のバイブル JSON を返す
- 抽出結果が `DomainProfileModel` にパース可能か検証

### ステップ 15: BibleExtractor.extract() の不正JSONテスト
- `llm.generate_json` が不正な JSON 文字列を返すようにモック
- パース失敗時のフォールバック（空バイブル or エラー）を確認

### ステップ 16: ContextBuilder.build() の境界値テスト
- 前話なし、キャラクターなし、プロットなしの各パターンで `build_context` を呼び出し、キー欠如・空文字が適切に処理されることを確認

---

## フェーズ3: APIエンドポイント統合テスト（ステップ 17-24）

### ステップ 17: テスト用コンテナ設定
`tests/integration/conftest.py` に `testcontainers.postgres.PostgresContainer` と `testcontainers.redis.RedisContainer` のフィクスチャを追加（または既存の SQLite/Redis モックを拡張）。

### ステップ 18: テスト用 FastAPI アプリ作成フィクスチャ
`create_app()` を呼び出し、DI コンテナをテスト用 DB/Redis/モック LLM に差し替えた `TestClient` を返すフィクスチャ `client` を定義。

### ステップ 19: /api/easy_mode/generate 正常系テスト
- 有効な `EasyModeRequest` を POST
- ステータス 202、レスポンスに `task_id` が含まれることを確認
- Huey タスクが enqueue されることをモック経由で検証

### ステップ 20: /api/easy_mode/generate バリデーションエラーテスト
- 必須フィールド欠如・型不正のリクエストを送信
- 422 Unprocessable Entity が返ることを確認

### ステップ 21: /api/refine_erotic 正常系テスト
- 有効な `RefineEroticRequest` を POST
- 202 と `task_id` が返ることを確認

### ステップ 22: /api/critique/optimize 正常系テスト
- 有効な `CritiqueOptimizeRequest` を POST
- 202 と `task_id` が返ることを確認

### ステップ 23: 認証エラーテスト
- `X-API-Key` ヘッダーなしで上記エンドポイントを呼び出し
- 401/403 が返ることを確認

### ステップ 24: レートリミットテスト
- 同一 IP/キーで短時間に閾値以上リクエストを送信
- 429 Too Many Requests が返ることを確認

---

## 実装順序の推奨
1. フェーズ1（ステップ 1-8）から着手 — 依存関係が少なく、すぐに成果が出る
2. フェーズ2（ステップ 9-16）— モック技術の習得に役立つ
3. フェーズ3（ステップ 17-24）— インフラ（コンテナ）準備が必要なため最後に実施

## 完了基準
- 各ステップのテストが `pytest -xvs tests/...` でグリーンになる
- 全ステップ完了後、`pytest --cov=src --cov-report=term-missing` で対象モジュールのカバレッジが **+10% 以上** 向上していること