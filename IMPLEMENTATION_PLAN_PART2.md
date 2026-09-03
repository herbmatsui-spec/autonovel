# 統合テスト・API・Redis・ドキュメント実装計画書（20ステップ）

> 対象: 統合テスト作成 / APIエンドポイント追加 / Redis Streams対応 / ドキュメント更新

---

## フェーズ A: 統合テスト作成（ステップ 1〜6）

### Step 1: `tests/integration/test_full_pipeline.py` 新規作成 ✅
- **内容**: モック LLM / モック Repo で Planning → Marketing まで一気通しテスト
- **検証項目**:
  - `Orchestrator.run()` が全 8 ノードを順に実行すること
  - `final_ctx.artifacts` に `zip_data`, `zip_filename`, `drafted_text` が含まれること
  - `EventBus` に各エージェントの start/completed イベントが流れること
- **完了基準**: `pytest tests/integration/test_full_pipeline.py -v` パス

### Step 2: モックヘルパー追加 `tests/mocks/__init__.py` 拡充 ✅
- `MockLLMAdapter.generate_json()` / `generate_text()` スタブ
- `MockBookRepository` (get_book, get_plot, get_chapter 等を dict で返す)
- `MockImageService` (generate → 固定 URL 返す)
- `MockPlotAgent`, `MockWritingAgent`, `MockAuditAgent`, `MockMarketingAgent`, `MockIllustrationAgent`

### Step 3: 統合テストシナリオ追加 ✅
- **シナリオ A**: 正常系（全エージェント合格）
- **シナリオ B**: AuditAgent で不合格 → WritingAgent リトライ → 合格
- **シナリオ C**: IllustrationAgent でエラー → MarketingAgent まで継続

### Step 4: 既存 easy_mode テストとの共存確認 ✅
- `tests/test_plan_workflow.py`, `tests/test_writing_workflow.py` が壊れないこと
- `pytest tests/test_plan_workflow.py tests/test_writing_workflow.py tests/integration/test_full_pipeline.py -v` 全パス

### Step 5: CI 設定確認 (スキップ - 既存設定利用)
### Step 6: カバレッジ除外設定 (スキップ - 既存設定利用)

---

## フェーズ B: API エンドポイント追加（ステップ 7〜11）

### Step 7: `src/backend/routers/orchestrated.py` 新規作成 ✅
- **エンドポイント**:
  - `POST /orchestrated/generate` - オーケストレーション版生成起動
  - `GET /orchestrated/status/{task_id}` - ステータスポーリング（既存流用）
  - `GET /orchestrated/export/{book_id}` - ZIP エクスポート（既存流用）
- **リクエストモデル**: `OrchestratedGenerateRequest` (book_id, title, synopsis, target_eps, genre, llm_config 等)
- **レスポンス**: `task_id` 即時返却（非同期）

### Step 8: `src/backend/server.py` にルーター登録 ✅
- `orchestrated.router` を FastAPI アプリに include

### Step 9: 簡易モードとの共存確認 (未完了 - 既存ルーターのインポート問題でブロック)
- 既存 `/easy_mode/generate` と並行して動作すること
- 同一 `BookRepository` / `Huey` キューを共有しても競合しないこと

### Step 10: API テスト追加 `tests/integration/test_orchestrated_api.py` (未完了 - 既存ルーターのインポート問題でブロック)
- `TestClient` で `/orchestrated/generate` → 202 Accepted 確認
- モックワーカーでタスク完了までシミュレート

### Step 11: OpenAPI ドキュメント自動生成確認 (未完了)

**注**: フェーズ B の Step 9-11 は、`src.core.container.AppContainer` が存在しない既存コードベースの問題により、既存ルーターのインポートがハングするためブロックされている。この問題が解決され次第再開可能。

---

## フェーズ C: Redis Streams 対応（ステップ 12〜16）

### Step 12: `src/agents/event_bus.py` Redis 実装追加 ✅
- `EventBus.__init__(use_redis: bool, redis_url: str)` に引数追加
- `publish()` で `XADD` 実行（Stream 名: `agent_events:{correlation_id}`）
- `start_redis()` / `stop_redis()` で接続管理

### Step 13: Redis 接続プール管理 `src/shared/redis_pool.py` 新規作成 ✅
- `get_redis_pool()` シングルトン
- `close_redis_pool()` クリーンアップ
- 設定は環境変数 `REDIS_URL` / `REDIS_MAX_CONNECTIONS`

### Step 14: `generation_tasks.py` で Redis 版 EventBus 注入 ✅
- 環境変数 `USE_REDIS_EVENTS=true` 時に `EventBus(use_redis=True)` を Orchestrator に渡す
- 本番 `docker-compose.prod.yml` に `USE_REDIS_EVENTS=true` 追加

### Step 15: コンシューマー例スクリプト `scripts/consume_events.py` 作成 ✅
- `XREADGROUP` でイベント購読 → ログ出力 / メトリクス送信
- 将来的に独立サービス化するための雛形

### Step 16: ローカル動作確認 (スキップ - Redis 環境要)

---

## フェーズ D: ドキュメント更新（ステップ 17〜20）

### Step 17: `IMPLEMENTATION_PLAN.md` チェックリスト完了マーク ✅
- 全 24 ステップ + 本計画 20 ステップを ✅ 化 (ブロック項目除く)

### Step 18: `README.md` 「4.3 マルチエージェント協調シーケンス」更新
### Step 19: `docs/architecture.md` 新規作成（任意）
### Step 20: `CHANGELOG.md` 追記