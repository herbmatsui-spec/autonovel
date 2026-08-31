# AutoNovel

AutoNovel は FastAPI + React 18 + TypeScript + Huey + SQLAlchemy で構築された小説生成エンジンです。「かんたんモード」での章生成と、作品データ一式の ZIP エクスポートを提供します。

[![CI](https://github.com/herbmatsui-spec/autonovel/actions/workflows/ci.yml/badge.svg)](https://github.com/herbmatsui-spec/autonovel/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](#ライセンス)

---

## 目次

- [特徴](#特徴)
- [アーキテクチャ](#アーキテクチャ)
- [ディレクトリ構成](#ディレクトリ構成)
- [必要環境](#必要環境)
- [クイックスタート](#クイックスタート)
  - [ワンクリック起動 (Windows バッチ)](#ワンクリック起動-windows-バッチ)
  - [Docker Compose 起動](#docker-compose-起動)
  - [ローカル手動起動 (Windows PowerShell)](#ローカル手動起動-windows-powershell)
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
- 🐳 **本番対応**: マルチステージ Dockerfile、nginx リバースプロキシ、PostgreSQL 16 / Redis 7 の `docker-compose.prod.yml` を同梱。
- 📊 **オブザーバビリティ**: 構造化 JSON ロギング、詳細ヘルスチェック (`/health`)、プロセス内メトリクス (`/metrics`) を標準装備。

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
- **DB**: PostgreSQL 16 (本番・Docker開発) / SQLite (ローカル開発・テスト)。`DATABASE_URL` で切替。
- **Queue**: Redis 7 (本番・Docker開発) / SQLite (ローカル開発)。`HUEY_BACKEND=redis|sqlite` で切替。

---

## ディレクトリ構成

```
autonovel/
├── src/
│   ├── backend/
│   │   ├── server.py              # FastAPI アプリ + lifespan
│   │   ├── observability.py       # ヘルスチェック・軽量メトリクスカウンタ
│   │   ├── database/
│   │   │   ├── __init__.py        # engine, SessionLocal, init_db()
│   │   │   └── repository.py      # BookRepository (Task/Book/Chapter/...)
│   │   ├── routers/
│   │   │   └── easy_mode.py       # /easy_mode/* エンドポイント
│   │   ├── tasks/
│   │   │   ├── huey.py            # Huey インスタンス
│   │   │   └── generation_tasks.py# generate_chapter_task
│   │   └── logging_config.py      # structlog 風の JSON / テキストログ設定
│   ├── models/                    # SQLAlchemy モデル + Pydantic スキーマ
│   └── services/                  # digest_service / marketing (export)
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api/easyMode.ts        # API クライアント (fetch)
│   │   ├── components/            # GeneratePanel / ExportPanel
│   │   └── types/easyMode.ts
│   ├── Dockerfile                 # マルチステージ (dev / production nginx)
│   └── tests/                     # Vitest
├── tests/                         # pytest (backend)
│   ├── conftest.py                # real_db_manager (engine 差替え)
│   ├── test_health.py
│   └── integration/
├── scripts/
│   ├── release.ps1                # バージョンタグ付きリリース
│   ├── smoke_test.ps1             # 5 エンドポイントの smoke test
│   ├── generate_openapi.py        # docs/openapi.json 生成・差分検知
│   ├── sync_reqs.py               # 依存関係同期スクリプト
│   └── verify_all.ps1             # 全検証一括実行
├── docs/api.md                    # API リファレンス
├── .github/workflows/ci.yml       # backend / frontend パイプライン
├── Dockerfile                     # バックエンド (マルチステージ)
├── docker-compose.yml             # 開発用 (PostgreSQL + Redis + Vite dev)
├── docker-compose.prod.yml        # 本番用 (PostgreSQL + Redis + Nginx)
├── Makefile                       # install/dev/test/lint/typecheck/run/...
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── CHANGELOG.md
├── SECURITY.md
├── CONTRIBUTING.md
├── アプリ起動.bat                 # Windows用 Docker Compose 一括起動バッチ
└── アプリ起動_ローカル.bat         # Windows用 ローカルPython/Vite 一括起動バッチ
```

---

## 必要環境

- **Python** 3.12 以上
- **Node.js** 18 以上 (フロントエンドビルド・開発時)
- **Docker** 24 以上 + Docker Compose v2 (コンテナ実行時)
- Windows では PowerShell 7 推奨 (`アプリ起動.bat` / `アプリ起動_ローカル.bat` 利用可)

---

## クイックスタート

### ワンクリック起動 (Windows バッチ)

Windows 環境では、付属のバッチファイルをダブルクリックするだけで起動できます。

- **`アプリ起動.bat`** (Docker Compose 推奨):
  - Docker Compose を利用して Backend, Worker, Frontend (dev), PostgreSQL, Redis を一括起動します。
  - 起動後、自動的にブラウザで `http://localhost:5173` が開きます。
- **`アプリ起動_ローカル.bat`** (ローカル Python + Vite):
  - ローカルの `.venv` と SQLite を利用して、Backend, Worker, Frontend をそれぞれ別ウィンドウで一括起動します。
  - 事前に `py -m venv .venv` および `pip install -r requirements-dev.txt`、`cd frontend && npm install` を完了させておく必要があります。
  - 起動後、自動的にブラウザで `http://localhost:5173` が開きます。

---

### Docker Compose 起動

#### 開発環境 (Hot Reload 有効)

```powershell
docker compose up --build
# フロントエンド (Vite dev): http://localhost:5173
# バックエンド (FastAPI)   : http://localhost:8200
```

#### 本番構成 (Nginx リバースプロキシ + PostgreSQL + Redis)

```powershell
docker compose -f docker-compose.prod.yml up -d --build
# フロントエンド (Nginx経由): http://localhost:8080
# バックエンド API (内部)   : 8200
# ※ postgres / redis は内部ネットワークのみに公開
```

停止する場合:

```powershell
docker compose down
# 本番環境の場合:
# docker compose -f docker-compose.prod.yml down
```

---

### ローカル手動起動 (Windows PowerShell)

Docker を使わずにローカルの Python / Node 環境で起動する場合の手順です。

```powershell
# 1. Python 仮想環境の作成と依存関係のインストール
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements-dev.txt
py -m pip install -e .

# 2. フロントエンド依存関係のインストール
cd frontend; npm install; cd ..

# 3. 環境変数の設定 (SQLite モード)
$env:HUEY_BACKEND = "sqlite"
$env:DATABASE_URL = "sqlite:///./autonovel.db"

# 4. バックエンド起動 (ターミナル 1)
py -m uvicorn src.backend.server:app --reload --port 8200

# 5. ワーカー起動 (ターミナル 2)
py -m huey.bin.huey_consumer src.backend.tasks.huey.huey

# 6. フロントエンド起動 (ターミナル 3)
cd frontend
npm run dev
# ブラウザで http://localhost:5173 にアクセス
```

---

## 開発ワークフロー

主要な操作は `Makefile` または PowerShell スクリプトで簡単に実行できます。

| コマンド | 内容 |
|----------|------|
| `make install` | バックエンド依存関係をインストール (`pip install -r requirements-dev.txt -e .`) |
| `make dev` | フロントエンドの依存関係も含めてセットアップ (`cd frontend && npm install`) |
| `make test` | バックエンドの単体・統合テストを実行 (`pytest -q --tb=short`) |
| `make lint` | ruff によるコード静的解析 (`ruff check src tests`) |
| `make typecheck` | mypy による型チェック (`mypy src`) |
| `make openapi` | OpenAPI 仕様書を `docs/openapi.json` に再生成 |
| `make frontend-test` | フロントエンドの Vitest テストを実行 |
| `make frontend-lint` | フロントエンドの ESLint と 型チェックを実行 |
| `make run` | バックエンド開発サーバー単体を起動 (Port 8200) |
| `make dev-up` / `make dev-down` | Docker Compose 開発環境の起動 / 停止 |
| `make prod-up` / `make prod-down` | Docker Compose 本番構成の起動 / 停止 |
| `make verify` | lint + typecheck + test + openapi + frontend-lint + frontend-test の全検証を一括実行 |
| `make clean` | キャッシュ (`.pytest_cache`, `__pycache__`) や一時 DB を削除 |

PowerShell スクリプトで全検証を行う場合:

```powershell
.\scripts\verify_all.ps1
```

---

## API エンドポイント

Base URL (開発時): `http://localhost:8200` (Nginx 本番時: `http://localhost:8080`)

| Method | Path | 説明 |
|--------|------|------|
| `GET`  | `/health` | ヘルスチェック (DB / Huey 生存確認 + メトリクススナップショット。`status` は `ok` / `degraded`) |
| `GET`  | `/metrics` | プロセス内メトリクスカウンタのスナップショット (タスク/エクスポート/ヘルスチェック件数) |
| `POST` | `/easy_mode/generate` | 章生成タスクを Huey キューに投入し `suggestions` に task ID を返却 |
| `GET`  | `/easy_mode/status/{task_id}` | タスクのステータス (`pending` / `success` / `failed`) と生成結果を取得 |
| `GET`  | `/easy_mode/export/{book_id}` | 指定 `book_id` の ZIP エクスポート (`book_id >= 1`、違反時は 422) |

詳細なスキーマ定義とリクエスト/レスポンス例は [`docs/api.md`](docs/api.md) を参照してください。
OpenAPI 仕様書は `python scripts/generate_openapi.py` で `docs/openapi.json` として生成できます。

---

## 環境変数

`.env.example` を参考に `.env` を作成して設定してください。

| 変数 | 既定値 | 説明 |
|------|--------|------|
| `DATABASE_URL` | `postgresql://autonovel:autonovel@db:5432/autonovel` | SQLAlchemy 接続 URL。SQLite 利用時は `sqlite:///./autonovel.db`。 |
| `REDIS_URL` | `redis://redis:6379/0` | Redis 接続 URL (`HUEY_BACKEND=redis` 時に使用)。 |
| `HUEY_BACKEND` | `redis` | `redis` または `sqlite`。開発・ローカル時は `sqlite` で Redis 不要。 |
| `LOG_LEVEL` | `INFO` | ルートロガーのログレベル (`DEBUG`, `INFO`, `WARNING`, `ERROR`)。 |
| `LOG_FORMAT` | `json` | ログ形式 (`json`: python-json-logger による構造化ログ、`text`: プレーンテキスト)。 |
| `APP_ENV` | `local` | デプロイ環境識別子 (`local`, `dev`, `prod` など)。全ログの `env` フィールドに付与。 |
| `LOG_LEVEL_<NAME>` | (なし) | 特定ロガー `<NAME>` のレベル個別上書き (例: `LOG_LEVEL_HUEY=DEBUG`)。 |

---

## オブザーバビリティ

AutoNovel では運用信頼性と保守性を高めるため、構造化ロギング・詳細ヘルスチェック・軽量メトリクスを標準装備しています。

### 構造化ロギング

`src/backend/logging_config.py` により `python-json-logger` を用いた JSON ログ出力を提供します。
全ログレコードには以下の共通コンテキストが自動付与されます:

| フィールド | 内容 |
|------------|------|
| `app`       | `autonovel` |
| `version`   | パッケージバージョン (`0.2.0`) |
| `env`       | `APP_ENV` 環境変数の値 (既定: `local`) |

主要処理で構造化ログが出力されます:
- タスク投入 (`Enqueued generation task`)
- 生成完了 / 失敗 (`Generation task completed` / `failed`)
- エクスポート要求 / 成功 (`Export requested` / `succeeded`)
- ステータスポーリング / ヘルスチェック呼出

### ヘルスチェック (`GET /health`)

DB 接続確認 (`SELECT 1`) と Huey バックエンド (`len(huey)`) の生存確認を同期的に実施し、メトリクススナップショットを含むペイロードを返します。

- 全コンポーネント正常時: `"status": "ok"`
- いずれか異常時: `"status": "degraded"` (HTTP 200 を維持しつつ状態を明示)

### メトリクス (`GET /metrics`)

プロセス内カウンタ (`src/backend/observability.py`) により以下のメトリクスを追跡可能です:

| メトリクス名 | カウント対象 |
|--------------|--------------|
| `tasks_enqueued` | `POST /easy_mode/generate` の投入成功数 |
| `tasks_completed` | `generate_chapter_task` の完了成功数 |
| `tasks_failed` | `generate_chapter_task` の例外失敗数 |
| `exports_attempted` | `GET /easy_mode/export/{book_id}` の呼出回数 |
| `exports_succeeded` | エクスポート ZIP の生成成功数 |
| `health_checks` | `GET /health` の呼出回数 |

---

## 本番デプロイ

```powershell
# 1. .env を本番用に構成
Copy-Item .env.example .env

# 2. 本番用コンテナ起動
docker compose -f docker-compose.prod.yml up -d --build

# 3. 状態・ヘルスチェック確認
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8080/health

# 4. スモークテスト実行
.\scripts\smoke_test.ps1 -BaseUrl http://localhost:8080
```

セキュリティ方針・脆弱性報告フローは [SECURITY.md](SECURITY.md) を参照してください。

---

## テスト

### バックエンド (pytest)

```powershell
py -m pytest -q --tb=short
```

- `asyncio_mode=auto` により `@pytest.mark.asyncio` は不要です。
- `tests/conftest.py` の `real_db_manager` フィクスチャがテスト用 engine/SessionLocal を一時 DB に差し替え、テスト後に安全にクリーンアップします。

### フロントエンド (Vitest)

```powershell
cd frontend
npm run test:ci
```

### スモークテスト (E2E 検証)

稼働中のサーバーに対してエンドツーエンド検証を実行します:

```powershell
.\scripts\smoke_test.ps1 -BaseUrl http://localhost:8200
```

---

## リリースフロー

```powershell
# 1. pyproject.toml の version を更新
# 2. CHANGELOG.md にリリースノートを追加
# 3. リリーススクリプトを実行 (検証 + git tag 作成)
.\scripts\release.ps1 -Tag v0.2.0
git push origin v0.2.0
```

詳細は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。

---

## ドキュメント

- [`docs/api.md`](docs/api.md) — REST API リファレンス
- [`CHANGELOG.md`](CHANGELOG.md) — 変更履歴 (Semantic Versioning 準拠)
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — 開発環境構築・コーディング規約・PR フロー
- [`SECURITY.md`](SECURITY.md) — セキュリティポリシー・脆弱性報告フロー
- [`plans/implementation_plan_72steps.md`](plans/implementation_plan_72steps.md) — 実装計画ドキュメント

---

## セキュリティ

脆弱性を発見した場合は、GitHub の公開 Issue ではなく [SECURITY.md](SECURITY.md) に記載の手順に従い非公開レポートをお願いします。

---

## コントリビュート

コントリビューションを歓迎します。作業を開始する前に [CONTRIBUTING.md](CONTRIBUTING.md) をご確認ください。
コミットメッセージは [Conventional Commits](https://www.conventionalcommits.org/) を推奨します。

---

## ライセンス

[MIT License](LICENSE) (詳細はリポジトリのライセンス表記を参照してください)。
