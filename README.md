# AutoNovel

AutoNovel は FastAPI + React 18 + TypeScript + Huey + SQLAlchemy で構築された小説生成エンジンです。「かんたんモード」での章生成と、作品データ一式の ZIP エクスポートを提供します。

[![CI](https://github.com/autonovel/autonovel/actions/workflows/ci.yml/badge.svg)](https://github.com/autonovel/autonovel/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](#ライセンス)

---

## 目次

- [特徴](#特徴)
- [アーキテクチャ](#アーキテクチャ)
- [ディレクトリ構成](#ディレクトリ構成)
- [必要環境](#必要環境)
- [クイックスタート](#クイックスタート)
  - [Docker compose (推奨)](#docker-compose-推奨)
  - [ローカル開発 (Windows PowerShell)](#ローカル開発-windows-powershell)
- [開発ワークフロー](#開発ワークフロー)
- [API エンドポイント](#apiエンドポイント)
- [環境変数](#環境変数)
- [オブザーバビリティ](#オブザーバビリティ)
- [本番デプロイ](#本番デプロイ)
- [テスト](#テスト)
- [リリースフロー](#リリースフロー)
- [ドキュメント](#ドキュメント)
- [セキュリティ](#セキュリティ)
- [コントリビュート](#コントリビュート)
- [ライセンス](#ライセンス)

---

## 特徴

- ✨ **かんたんモード**: 章履歴・キャラクタ設定を与えるだけで次章を生成。Huey タスクキューで非同期実行し、ステータスポーリングで結果を取得。
- 📦 **ZIP エクスポート**: 作品本文・設定・プロット・JSON ダンプを 1 つの ZIP アーカイブにまとめて即ダウンロード。
- 🧱 **モダンスタック**: FastAPI (async) + SQLAlchemy 2.x + Huey (Redis/SQLite バックエンド切替可) + React 18 + Vite + TypeScript (strict)。
- 🧪 **テスト駆動**: pytest (asyncio_mode=auto) + Vitest。`real_db_manager` フィクスチャで実 DB セッションを用いた統合テストを実装。
- 🔍 **品質ゲート**: ruff (lint/format) + mypy (strict) + OpenAPI schema 生成・差分検知を CI で実施。
- 🐳 **本番対応**: マルチステージ Dockerfile、nginx リバースプロキシ、PostgreSQL 16 / Redis 7 の docker-compose.prod.yml を同梱。

---

## アーキテクチャ

```
┌────────────┐    HTTP     ┌─────────────┐    SQLAlchemy    ┌─────────────┐
│  React UI  │ ─────────▶  │  FastAPI    │ ──────────────▶ │ PostgreSQL  │
│ (Vite/TS)  │ ◀─────────  │  (uvicorn)  │ ◀────────────── │   (本体)    │
└────────────┘             └─────────────┘                  └─────────────┘
                                  │ enqueue
                                  ▼
                           ┌─────────────┐    dequeue       ┌─────────────┐
                           │   Huey      │ ───────────────▶ │   Redis     │
                           │  (worker)   │                  └─────────────┘
                           └─────────────┘
                                  │
                                  ▼
                           LLM 生成 (generate_chapter_task)
                           結果を DB へ永続化し task レコードをクリーンアップ
```

- **backend**: FastAPI アプリ (`src/backend/server.py`)。lifespan で `init_db()` を実行。
- **worker**: Huey consumer (`src/backend/tasks/huey.py`)。`generate_chapter_task` を実行し、成功時に `_persist_success` で結果を DB に保存して task 行を削除。
- **frontend**: Vite + React 18 + TypeScript (strict)。`frontend/Dockerfile` でビルド後 nginx で配信し `/easy_mode/*` をバックエンドへリバースプロキシ。
- **DB**: PostgreSQL 16 (本番) / SQLite (開発・テスト)。`DATABASE_URL` で切替。
- **Queue**: Redis 7 (本番) / SQLite (開発)。`HUEY_BACKEND=redis|sqlite` で切替。

---

## ディレクトリ構成

```
autonovel/
├── src/
│   ├── backend/
│   │   ├── server.py              # FastAPI アプリ + lifespan
│   │   ├── database/
│   │   │   ├── __init__.py        # engine, SessionLocal, init_db()
│   │   │   └── repository.py      # BookRepository (Task/Book/Chapter/...)
│   │   ├── routers/
│   │   │   └── easy_mode.py       # /easy_mode/* エンドポイント
│   │   ├── tasks/
│   │   │   ├── huey.py            # Huey インスタンス
│   │   │   └── generation_tasks.py# generate_chapter_task
│   │   └── logging_config.py     # structlog 風の JSON ログ設定
│   ├── models/                    # SQLAlchemy モデル + Pydantic スキーマ
│   └── services/                  # digest_service / marketing (export)
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/easyMode.ts        # API クライアント (fetch)
│   │   ├── components/            # GeneratePanel / ExportPanel
│   │   └── types/easyMode.ts
│   ├── Dockerfile                 # マルチステージ → nginx
│   └── tests/                     # Vitest
├── tests/                         # pytest (backend)
│   ├── conftest.py                # real_db_manager (engine 差替え)
│   ├── test_health.py
│   └── integration/
├── scripts/
│   ├── release.ps1                # バージョンタグ付きリリース
│   ├── smoke_test.ps1             # 5 エンドポイントの smoke test
│   ├── generate_openapi.py        # docs/openapi.json 生成・差分検知
│   └── verify_all.ps1
├── docs/api.md                    # API リファレンス
├── .github/workflows/ci.yml       # backend / frontend パイプライン
├── Dockerfile                     # バックエンド (マルチステージ)
├── docker-compose.yml             # 開発用
├── docker-compose.prod.yml        # 本番用 (postgres + redis + healthcheck)
├── Makefile                       # install/dev/test/lint/typecheck/run/...
├── pyproject.toml
├── CHANGELOG.md
├── SECURITY.md
└── CONTRIBUTING.md
```

---

## 必要環境

- **Python** 3.12 以上
- **Node.js** 18 以上 (frontend ビルド)
- **Docker** 24 以上 + Docker Compose v2 (コンテナ実行時)
- Windows では PowerShell 7 推奨 (`アプリ起動.bat` も利用可)

---

## クイックスタート

### Docker compose (推奨)

#### 開発

```powershell
docker compose up --build
# backend: http://localhost:8200
# frontend: http://localhost:8080
```

#### 本番

```powershell
docker compose -f docker-compose.prod.yml up -d --build
# backend (internal): 8200
# frontend (nginx): http://localhost:8080
# postgres / redis は内部ネットワークのみ
```

### ローカル開発 (Windows PowerShell)

```powershell
# 1. Python 仮想環境
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements-dev.txt

# 2. フロントエンド依存関係
cd frontend; npm install; cd ..

# 3. 全検証 (lint + typecheck + pytest + frontend test)
.\scripts\verify_all.ps1

# 4. バックエンド起動
uvicorn src.backend.server:app --reload --port 8200

# 5. (別ターミナル) ワーカー起動
huey_consumer src.backend.tasks.huey.huey

# 6. (別ターミナル) フロントエンド起動
cd frontend; npm run dev
```

> `アプリ起動.bat` を実行するとバックエンド + ワーカーを 1 コマンドで起動できます (`uvicorn` と `huey_consumer` を並列起動)。

---

## 開発ワークフロー

主要な操作は `Makefile` にエイリアスを用意しています。

| Make ターゲット | 内容 |
|----------------|------|
| `make install` | `pip install -r requirements-dev.txt` + `npm install` |
| `make dev` | backend と frontend を並列起動 |
| `make test` | `pytest -q --tb=short` |
| `make lint` | `ruff check src tests` |
| `make typecheck` | `mypy src` |
| `make openapi` | `python scripts/generate_openapi.py` |
| `make frontend-test` | `cd frontend && npm run test:ci` |
| `make verify` | lint + typecheck + test + openapi + frontend-test |
| `make prod-up` | `docker compose -f docker-compose.prod.yml up -d --build` |
| `make clean` | `__pycache__` / `.pytest_cache` / `*.db` などを掃除 |

CI と同じ検証をローカルで再現するには:

```powershell
py -m ruff check src tests
py -m mypy src
py -m pytest -q --tb=short --strict-markers
python scripts/generate_openapi.py
cd frontend; npm run typecheck; npm run lint; npm run test:ci; cd ..
```

---

## APIエンドポイント

Base URL (開発時): `http://localhost:8200`

| Method | Path | 説明 |
|--------|------|------|
| `GET`  | `/health` | ヘルスチェック (DB / Huey 生存 + メトリクススナップショットを含む。`status` は `ok` / `degraded`) |
| `GET`  | `/metrics` | プロセス内メトリクスカウンタのスナップショット (タスク/エクスポート/ヘルスチェック件数) |
| `POST` | `/easy_mode/generate` | 章生成タスクをキュー投入し `suggestions` に task ID を返す |
| `GET`  | `/easy_mode/status/{task_id}` | タスクstatus (`pending` / `success` / `failed`) と result を取得 |
| `GET`  | `/easy_mode/export/{book_id}` | 指定 book_id の ZIP エクスポート (`book_id` >= 1、違反時 422) |

リクエスト/レスポンスの詳細なスキーマは [`docs/api.md`](docs/api.md) を参照してください。
OpenAPI 仕様書は `python scripts/generate_openapi.py` で `docs/openapi.json` として生成できます (CI で差分検知を実施)。

---

## 環境変数

`.env.example` をベースに `.env` を作成してください。

| 変数 | 既定値 | 説明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql://autonovel:autonovel@db:5432/autonovel` | SQLAlchemy 接続 URL。`sqlite:///./autonovel.db` でローカル SQLite。 |
| `REDIS_URL` | `redis://redis:6379/0` | Redis 接続 URL (`HUEY_BACKEND=redis` 時に使用)。 |
| `HUEY_BACKEND` | `redis` | `redis` または `sqlite`。開発時は `sqlite` で Redis 不要。 |
| `LOG_LEVEL` | `INFO` | ルートロガーのログレベル。 |
| `LOG_FORMAT` | `json` | `json` (python-json-logger) または `text`。 |
| `APP_ENV` | `local` | デプロイ環境識別子。全ログレコードの `env` フィールドに付与される。 |
| `LOG_LEVEL_<NAME>` | (なし) | 特定ロガー `<NAME>` のレベル上書き (例: `LOG_LEVEL_HUEY=DEBUG`)。 |

> 開発用 `docker-compose.yml` は SQLite、本番用 `docker-compose.prod.yml` は PostgreSQL + Redis を使用します。

---

## オブザーバビリティ

AutoNovel は Phase 5 で構造化ロギング・ヘルスチェック・軽量メトリクスを整備している。

### 構造化ロギング

`src/backend/logging_config.py` が `python-json-logger` を用いた JSON ログ出力を既定で構成する。
全レコードには以下のコンテキストが常時付与される:

| フィールド | 内容 |
|------------|------|
| `app`       | `autonovel` |
| `version`   | パッケージバージョン |
| `env`       | `APP_ENV` 環境変数 (既定 `local`) |

- `LOG_FORMAT=text` でプレーンテキストフォーマットに切替可能
- `LOG_LEVEL_HUEY=DEBUG` のように `LOG_LEVEL_<NAME>` でロガー別のレベル上書きが可能
- 以下の重要処理で構造化ログを出力:
  - タスク投入 (`Enqueued generation task`)
  - 生成完了/失敗 (`Generation task completed/failed`)
  - エクスポート要求/成功 (`Export requested/succeeded`)
  - タスクステータスポーリング
  - ヘルスチェック呼出

### ヘルスチェック (`GET /health`)

DB 接続 (`SELECT 1`) と Huey バックエンド (`len(huey)`) の生存確認を同期的に実施し、
メトリクススナップショットを含めた総合ペイロードを返す。

- 全コンポーネント正常時: `status = "ok"`
- いずれか異常時: `status = "degraded"` (HTTP 200 を維持、監視は `status` フィールドで判定)
- 後方互換: 従来の `{"status": "ok"}` のスーパーセット

### メトリクス (`GET /metrics`)

外部依存を持たないプロセス内カウンタ (`src/backend/observability.py`) を提供する。
本格運用では Prometheus 等の外部ストアに置換可能 (拡張ポイント)。

| メトリクス          | 増加タイミング                              |
|--------------------|----------------------------------------------|
| `tasks_enqueued`   | `POST /easy_mode/generate` がキュー投入成功   |
| `tasks_completed`  | `generate_chapter_task` 成功                 |
| `tasks_failed`     | `generate_chapter_task` 例外失敗             |
| `exports_attempted`| `GET /easy_mode/export/{book_id}` 呼出       |
| `exports_succeeded`| エクスポート ZIP 生成成功                     |
| `health_checks`    | `GET /health` 呼出                            |

---

## 本番デプロイ

```powershell
# 1. .env を本番用に編集
Copy-Item .env.example .env
# DATABASE_URL / REDIS_URL を本番の接続先に変更

# 2. 起動
docker compose -f docker-compose.prod.yml up -d --build

# 3. ヘルスチェック
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8080/health   # nginx 経由

# 4. スモークテスト
.\scripts\smoke_test.ps1 -BaseUrl http://localhost:8080
```

デプロイのベストプラクティス・脆弱性報告フローは [SECURITY.md](SECURITY.md) を参照してください。

---

## テスト

### バックエンド (pytest)

```powershell
py -m pytest -q --tb=short
```

- `asyncio_mode=auto` (`pyproject.toml`) により `@pytest.mark.asyncio` 不要。
- `tests/conftest.py` の `real_db_manager` フィクスチャがテスト用 engine/SessionLocal を一時 DB に差し替え、各テスト後に元に戻します。
- 統合テストでは FastAPI lifespan を確実に走らせるため `with TestClient(app) as c:` パターンを使用 (`init_db()` が呼ばれ `tasks` テーブルが生成されます)。

### フロントエンド (Vitest)

```powershell
cd frontend
npm run test:ci
```

### スモークテスト (稼働中サービスに対する E2E)

```powershell
.\scripts\smoke_test.ps1 -BaseUrl http://localhost:8200
```

`/health` → POST `/easy_mode/generate` → GET `/easy_mode/status/{task_id}` → GET `/easy_mode/export/0` (422 期待) → GET `/easy_mode/export/1` (200/404 期待、500 は不可) を検証します。

---

## リリースフロー

```powershell
# 1. pyproject.toml の version を bump
# 2. CHANGELOG.md に新バージョンセクションを追加
# 3. リリーススクリプトで検証 + タグ作成
.\scripts\release.ps1 -Tag v0.2.0
git push origin v0.2.0
```

`release.ps1` は `ruff check` / `pytest` / OpenAPI 生成 / frontend typecheck を実行後、`git tag` を作成し CHANGELOG の該当バージョン区間を抜き出します。詳細は [CONTRIBUTING.md](CONTRIBUTING.md) の「Release flow」セクションを参照してください。

---

## ドキュメント

- [`docs/api.md`](docs/api.md) — REST API リファレンス
- [`CHANGELOG.md`](CHANGELOG.md) — バージョンごとの変更履歴
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — 開発環境セットアップ・コーディング規約・PR 運用
- [`SECURITY.md`](SECURITY.md) — サポートバージョン・脆弱性報告フロー
- [`plans/implementation_plan_72steps.md`](plans/implementation_plan_72steps.md) — 実装計画 (72 ステップ)

---

## セキュリティ

脆弱性を発見した場合は [SECURITY.md](SECURITY.md) の手順に従い、公開 Issue ではなく非公開レポートをお願いします。

---

## コントリビュート

プルリク歓迎です。始める前に [CONTRIBUTING.md](CONTRIBUTING.md) をお読みください。
ブランチ命名は `feature/<slug>` / `fix/<slug>`、コミットは Conventional Commits を推奨します。

---

## ライセンス

MIT License. 詳細は `LICENSE` ファイル (存在する場合) またはリポジトリのライセンス表記を参照してください。
