# Changelog

本プロジェクトの変更履歴。[Semantic Versioning](https://semver.org/lang/ja/) に準拠。

## [Unreleased] - Multimedia (Phase 7)

マルチメディア展開 (Asset Pack / Media Mix / IF Routes / eBook Export) の初回統合リリース。
3,700 行の孤児コードを FastAPI ルータ + React UI から利用可能にし、機能フラグ `ENABLE_MULTIMEDIA` で段階ロールアウト可能化。

### 追加
- **機能フラグ**: `ENABLE_MULTIMEDIA` / `ENABLE_AUDIO_SYNTH` / `MULTIMEDIA_OUTPUT_DIR` を `config.py` に追加
- **バックエンド**:
  - `routers/multimedia.py` (8 エンドポイント: `/multimedia/media-mix`, `/ebook`, `/if-routes`, `/asset-pack`, `/artifacts/{id}`, `/artifacts/{id}/download`, `/tasks/{id}`, `/files/{filename}`)
  - `multimedia_service.py` 統合サービス層
  - `multimedia_storage.py` 出力ディレクトリ管理
  - `feature_flags.py` フラグ判定ユーティリティ
  - `tasks/multimedia_tasks.py` Huey 非同期タスク
  - `schemas/multimedia.py` Pydantic スキーマ
  - `MultimediaArtifact` / `MultimediaTask` テーブル (alembic 0011)
  - `MultimediaDisabledError` (HTTP 503)
  - `series_serializer.py` ユーティリティ
- **フロントエンド**:
  - `types/multimedia.ts` 型定義
  - `api/multimedia.ts` API クライアント
  - `hooks/useMultimedia.ts` React フック
  - `components/AssetPackPanel.tsx` Studio 統合
- **メトリクス**: `multimedia_requests_total` / `multimedia_errors_total` カウンタ追加
- **ドキュメント**: `docs/multimedia.md`, `docs/multimedia_slo.md`, `docs/multimedia_security.md`, `docs/user/multimedia.md`
- **アラート**: `docker/grafana/alerts/multimedia.yaml`

### テスト (54 件)
- `tests/unit/test_media_mix.py`, `test_ebook_export.py`, `test_asset_pack.py`, `test_multimedia_service.py`, `test_feature_flags.py`, `test_multimedia_storage.py`, `test_multimedia_schemas.py`, `test_series_serializer.py`, `test_multimedia_tasks.py`
- `tests/integration/test_multimedia_router.py`, `test_multimedia_e2e.py`
- `tests/unit/test_if_routes.py` 拡充 (BranchCondition.apply_effects, IFRouteGenerator minimum nodes, IFRouteGraph.validate)

### マイグレーション
- `alembic/versions/0011_multimedia_artifacts.py`: `multimedia_artifacts` / `multimedia_tasks` テーブル

## [4.0.0] - 2026-09-01

大規模リファクタリング・健全化リリース。タスク実行基盤の修復、ID二重管理の解消、テストカバレッジ・品質保証を大幅強化。

### 修正・改善
- **タスク実行基盤**: Huey タスク投入シグネチャの不整合を解消し、`generate_chapter_task` 呼び出しを正規化
- **ID統合**: DB の `Task.id` を UUID 文字列型へ刷新し、Huey タスクIDと完全同期。タスクキャンセル機能（`cancel_task`）が確実に反映されるよう改修
- **テスト・品質**: フロントエンドの Vitest カバレッジ基準をクリア（Funcs 55.5% / Stmts 85.2%）、Toast コンポーネント等の単体テストを追加
- **コードベース整理**: 未使用コンポーネント（`Sidebar.tsx`）および不要スクリプト（`sync_reqs.py`, `revenue_simulation.py`）を削除
- **ビルド・依存関係**: `Makefile` のインストールターゲットを `pip install -e .[dev]` に修正

## [Unreleased] - Phase 5: 品質・観測・ドキュメント (Step 51-62)

ロギング・オブザーバビリティ・ドキュメントの三点で運用信頼性と保守性を向上。

### 追加
- **オブザーバビリティ**: `src/backend/observability.py` 新設。DB 接続確認 (`SELECT 1`) と Huey 生存確認 (`len(huey)`) を統合した `build_health_payload` ([`src/backend/observability.py`](src/backend/observability.py))
- **メトリクス**: `GET /metrics` エンドポイント追加。プロセス内カウンタ (`tasks_enqueued` / `tasks_completed` / `tasks_failed` / `exports_attempted` / `exports_succeeded` / `health_checks`) を提供 ([`src/backend/server.py`](src/backend/server.py))
- **テスト**: `test_health.py` に拡充ヘルスチェック (`components` / `metrics`) と `/metrics` エンドポイントの検証を追加 ([`tests/test_health.py`](tests/test_health.py))

### 変更
- **ヘルスチェック**: `GET /health` を DB/Huey 生存 + メトリクススナップショットを含めた総合ペイロードへ拡充 (`status` は `ok` / `degraded`)。後方互換のため `{"status": "ok"}` のスーパーセット ([`src/backend/server.py`](src/backend/server.py))
- **ロギング**: `logging_config.py` 強化。`app` / `version` / `env` コンテキスト付与、`LOG_FORMAT` / `LOG_LEVEL_<NAME>` / `APP_ENV` 環境変数対応、ノイズロガー抑制 ([`src/backend/logging_config.py`](src/backend/logging_config.py))
- **重要処理ログ**: タスク投入 / 生成完了 / 生成失敗 / エクスポート要求・成功 / ステータスポーリング / ヘルスチェック呼出に構造化ログを追加 ([`src/backend/routers/easy_mode.py`](src/backend/routers/easy_mode.py), [`src/backend/tasks/generation_tasks.py`](src/backend/tasks/generation_tasks.py), [`src/services/marketing.py`](src/services/marketing.py))
- **メトリクス連携**: 主要処理 (タスク投入/完了/失敗・エクスポート試行/成功・ヘルスチェック) から `metrics.increment` を呼出し
- **ドキュメント**: `docs/api.md` を `/metrics` と拡充 `/health`・環境変数 (`LOG_FORMAT`, `APP_ENV`, `LOG_LEVEL_<NAME>`) で更新 ([`docs/api.md`](docs/api.md))
- **ドキュメント**: `docs/openapi.json` を `scripts/generate_openapi.py` で再生成 ([`docs/openapi.json`](docs/openapi.json), [`scripts/generate_openapi.py`](scripts/generate_openapi.py))
- **README**: API テーブルに `/health` (拡充版) / `/metrics` を追加、環境変数テーブル拡充、新規「オブザーバビリティ」セクション追加・目次更新 ([`README.md`](README.md))

## [0.2.0] - 2026-07-27

72 ステップ実装計画 (Phase 0-6) のうち Phase 0-5 を完了。バックエンド非同期生成フルロー、エクスポート ZIP、React 18 フロントエンド、CI/CD、Docker 本番構成を整備。

### 追加
- **バックエンド**: FastAPI lifespan ハンドラで `init_db()` を確実起動 ([`src/backend/server.py`](src/backend/server.py))
- **非同期生成**: Huey `generate_chapter_task` 実装、成功時に `_persist_success` で DB へ結果保存 → `delete_task` でクリーンアップ ([`src/backend/tasks/generation_tasks.py`](src/backend/tasks/generation_tasks.py))
- **エクスポート**: `MarketingAgent.create_export_package` が ZIP 生成、`Cache-Control: no-store` + RFC 6266 filename ヘッダ ([`src/services/marketing.py`](src/services/marketing.py))
- **バリデーション**: `book_id` に `Path(ge=1)`、`content_length_limit` に `Field(ge=1, le=10000)` (422 応答)
- **ロギング**: `python-json-logger` による JSON 構造化ログ ([`src/backend/logging_config.py`](src/backend/logging_config.py))
- **フロントエンド**: React 18 `createRoot` + GeneratePanel / ExportPanel / API クライアント + ポーリング ([`frontend/src/`](frontend/src/))
- **CI**: GitHub Actions バックエンド (ruff + pytest + OpenAPI 生成) & フロントエンド (typecheck + lint + test:ci) ([`.github/workflows/ci.yml`](.github/workflows/ci.yml))
- **OpenAPI 自動生成**: `scripts/generate_openapi.py` ([`scripts/generate_openapi.py`](scripts/generate_openapi.py))
- **ドキュメント**: API リファレンス ([`docs/api.md`](docs/api.md))
- **テスト**: `test_easy_mode_export.py` (実 DB・fallback・ZIP 内容検証)、`test_health.py` (200/422)、`test_generate_flow.py` (generate→status 統合)、`test_async_generation.py` (クリーンアップ検証)
- **Docker**: バックエンド multi-stage (builder→runtime slim)、フロントエンド nginx 配信 + `/easy_mode/` リバースプロキシ ([`Dockerfile`](Dockerfile), [`frontend/Dockerfile`](frontend/Dockerfile))

### 変更
- [`src/models/book.py`](src/models/book.py): `List`/`Optional` → `list[...]`/`X | None` モダン型ヒント
- [`src/backend/database/__init__.py`](src/backend/database/__init__.py): 未使用 import 削除 + `__all__` 整備
- [`src/backend/database/repository.py`](src/backend/database/repository.py): `is_(False)` 採用、近代化 typig
- [`src/services/marketing.py`](src/services/marketing.py): DB キャラクタ抽出に `personality`/`ability` を追加
- [`src/backend/routers/easy_mode.py`](src/backend/routers/easy_mode.py): `from src.backend import database` 形式へ統一 (テスト時 engine 差替え対応)
- `pyproject.toml`: pytest `asyncio_mode=auto`, `-q --tb=short --strict-markers`
- `requirements-dev.txt`: `pytest-cov`, `httpx`, `python-json-logger` 追加

### 削除
- 不要な空 stub パッケージ (`pydantic/`, `fastapi/`, `huey/`, `sqlalchemy/`) を削除 (sys.path 衝突回避)

### テスト結果
- pytest: 9 passed (バックエンド)
- フロントエンド: typecheck / lint / test:ci は CI 上で実行

## [4.1.0] - マルチエージェントオーケストレーション正式対応

8 エージェント (PlanningAgent / PlotAgent / BibleAgent / ContextBuilderAgent / WritingAgent / AuditAgent / IllustrationAgent / MarketingAgent) を **Orchestrator** パターンで統合。README の 8 エージェント構成を実装レベルで実現。

### 追加
- **コア基盤**:
  - `src/agents/orchestrator.py` - 型付きステートマシンによるエージェント順序実行・リトライ制御
  - `src/agents/event_bus.py` - インメモリ / Redis Streams 両対応の観測バス
  - `src/agents/context_builder_agent.py` - `ContextBuilder` をファーストクラスエージェント化（後方互換ラッパは非推奨化）
  - `src/agents/audit_agent.py` - 既存 6 監査クラスを統合したファサード
- **エージェント層**:
  - `PlanningAgent.run` / `PlotAgent.run` / `BibleAgent.run` / `WritingAgent.run` / `IllustrationAgent.run` / `MarketingAgent.run` のシグネチャを `AgentContext` 統一
  - `BaseAgent.run` の型ヒント統一 (`(ctx: AgentContext) -> AgentResult`)
- **バックエンド**:
  - `src/backend/routers/orchestrated.py` - 新規ルータ (`/orchestrated/generate`, `/orchestrated/status/{task_id}`, `/orchestrated/export/{book_id}`, `/orchestrated/task/{task_id}`)
  - `src/backend/server.py` - オーケストレーションルータ登録
  - `src/backend/tasks/generation_tasks.py` - `generate_chapter_orchestrated_task` 追加 (Orchestrator 経由のフルパイプライン)
- **Redis Streams 連携**:
  - `src/shared/redis_pool.py` - 接続プール管理
  - `scripts/consume_events.py` - コンシューマー雛形 (XREADGROUP)
  - `docker-compose.prod.yml` - `USE_REDIS_EVENTS=true` 環境変数追加
- **テスト**:
  - `tests/mocks/__init__.py` - MockLLMAdapter / MockBookRepository / MockImageService / MockPlotAgent / MockWritingAgent / MockAuditAgent / MockMarketingAgent / MockIllustrationAgent / `create_mock_orchestrator()`
  - `tests/integration/test_full_pipeline.py` - 5 シナリオ (正常系 / Auditリトライ / Illustrationエラー / EventBus統合 / artifacts 受け渡し)
- **ドキュメント**:
  - `docs/architecture.md` - クラス図・制御フロー・easy_mode 比較
  - `README.md §4.3` - Mermaid シーケンス図を実装に合わせて更新 (Orchestrator/EventBus を反映)
  - `IMPLEMENTATION_PLAN.md` / `IMPLEMENTATION_PLAN_PART2.md` - 実装計画

### 変更
- **README.md §3.2 / §12.1 / §12.2**:
  - LLM プロバイダ誤認修正: claude/ollama/vLLM は OpenAI 互換モードでのみアクセス可能
  - Mermaid 図の `Claude` / `LocalLLM` ノードを `OpenAICompat` に統合
- **`src/services/llm/factory.py`**:
  - `IMPLEMENTED_PROVIDERS = {"gemini", "openai", "mock"}` 制限
  - 未実装プロバイダ指定時に ERROR ログ + MockLLMAdapter フォールバック
- **`src/backend/config.py`**:
  - `LLM_PROVIDER: Literal["openai", "gemini", "mock"]` 型制限
  - デフォルトを `"mock"` に変更（本番事故防止）
- **`src/agents/context_builder.py`**:
  - `ContextBuilder` クラスに `DeprecationWarning` 付与（`ContextBuilderAgent` への移行推奨）

### 修正
- **Alembic マイグレーション統合**:
  - ルート `alembic/` 削除、`src/backend/alembic/versions/` に全ファイル統合
  - `0003_pgvector_chapter_chunks` / `0003_add_ai_assistant_config` のリビジョン重複解消（後者を `0004` にリネーム）
  - リビジョンチェーン: `0000 → 0001 → 0002 → 0003 → 0004 → 0011 → 0012 → 0013`
- **LLM プロバイダ誤認リスク**:
  - `claude` / `ollama` 直接指定時の警告ログ追加
  - README §3.2 の「5プロバイダ対応」記述を実装済み 3 プロバイダに修正

### 受け入れ基準
- [x] `Orchestrator.run()` が 8 エージェントを順に実行し `zip_data` を返却
- [x] `AuditAgent` 失敗時 `should_retry=true` で `WritingAgent` へ自動遷移
- [x] `EventBus` 経由で各エージェント start/completed イベントが発行
- [x] Redis Streams 有効化 (`USE_REDIS_EVENTS=true`) で XADD 実行
- [x] `LLM_PROVIDER=claude` 指定時に ERROR ログ出力 + Mock フォールバック
- [x] Alembic マイグレーション重複解消 (0003 → 0003 + 0004)
- [x] 既存 `tests/test_plan_workflow.py` / `tests/test_writing_workflow.py` 全パス
- [x] 新規 `tests/integration/test_full_pipeline.py` 5 シナリオ全パス

### 既知の制限
- `src.core.container.AppContainer` 不在により一部既存ルーターの動的ロードがハング。`/orchestrated/*` エンドポイントの TestClient テストは別途対応要。
- 並列エージェント実行は将来拡張（`AgentResult.next_agents: list[AgentName]`）。

## [0.1.0] - 初期リリース

FastAPI + SQLAlchemy + Huey の最小構成。easy_mode ルータープロトタイプ、Book/Chapter/Character/Plot/Bible モデル定義。
