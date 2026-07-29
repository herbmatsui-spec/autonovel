# Changelog

本プロジェクトの変更履歴。[Semantic Versioning](https://semver.org/lang/ja/) に準拠。

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

## [0.1.0] - 初期リリース

FastAPI + SQLAlchemy + Huey の最小構成。easy_mode ルータープロトタイプ、Book/Chapter/Character/Plot/Bible モデル定義。
