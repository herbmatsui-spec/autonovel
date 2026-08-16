# v3.4 - 72ステップ実装完了リリースノート

## 主な変更

- **文字化け完全除去**（Phase 1: ステップ 1-8）
- **DIコンテナ整理**（Phase 2: ステップ 9-18）: `AppContainer` エイリアス削除、プロバイダパス正規化
- **認証強化**（Phase 3: ステップ 19-28）: `AUTH_DISABLED` 警告・本番拒否、レート制限キー、IP 偽装耐性テスト
- **非同期実装の安全化**（Phase 4: ステップ 29-38）:
  - `async_wrapper.run_async` 非推奨化
  - レートリミッターのメモリリーク防止
  - `TimeoutMiddleware` 定数化
  - `asyncio.to_thread` → `executor_manager.run_io()` 統一
  - グローバルセマフォの DI 化準備（`get_concurrency_semaphore()`）
  - パイプラインキャンセル処理の即時伝播
- **LLMゲートウェイ分割**（Phase 5: ステップ 39-48）:
  - `GeminiApiClient` / `OpenAIApiClient` を `src/core/llm_clients/` に分離
  - `BaseLLMClient` 抽象クラスを導入
  - `LLMProviderFactory.get_client()` の戻り値型を `BaseLLMClient` に
  - `LLMGenerateResultProxy.generate_json/generate_text` のシグネチャを明示化
  - `generate()` を非推奨（NotImplementedError）に
- **エラーハンドリング統一**（Phase 6: ステップ 49-56）:
  - `safe_model_validate` の過剰な `except` を `PydanticUserError` に特定化し `LLMValidationError` へラップ
  - パイプラインのフォールバック例外がキャンセルを握りつぶさないよう修正
  - `EXCEPTION_HIERARCHY.md` を新設
- **設定・定数集約**（Phase 7: ステップ 57-64）:
  - タイムアウト値・レート制限値を `config/constants.py` に集約
  - `server.py` がこれらを参照するよう変更
  - パイプラインの `ep_num == 8/7` を `EP_FINAL` / `EP_CLIMAX` 定数に置換
- **テスト・ドキュメント整備**（Phase 8: ステップ 65-72）:
  - `test_async_utils`, `test_rate_limiter_unit`, `test_exceptions`, `test_observability` を新設
  - `SECURITY.md`, `MIGRATION_GUIDE.md` を新設

## マイグレーション

1. `.env.example` を参考に `.env` を作成
2. `ALLOWED_API_KEYS` を必ず設定
3. `AUTH_DISABLED=true` は本番環境で不可
4. `GeminiApiClient` / `OpenAIApiClient` のインポートを `src.core.llm_clients` に変更
5. `LLMGenerateResultProxy.generate()` の利用を `generate_text()` / `generate_json()` に移行

## 検証結果

- 関連単体テスト：全 PASS
- `ruff check` / `ruff format --check`：対象ファイルでクリーン
- 文字化け 0 件

## 既知の制限事項

- `src/llm/gemini_provider.py` / `src/llm/openai_provider.py` は `src.core.exceptions` から
  `LLMAuthenticationError` 等をインポートしているが、これらの例外は現在 `src.core.exceptions` に
  未定義（定義は `src/shared/errors.py` 等に散在）。後続の例外統一フェーズで解決予定。
- `LLMGenerateResultProxy.generate_json/generate_text` は前方互換のため `**kwargs` を維持。
