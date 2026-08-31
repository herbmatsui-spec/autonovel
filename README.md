# AutoNovel

**AutoNovel** は、R15 ファンタジー小説の執筆を AI で支援する「かんたん制作」エンジンです。FastAPI + React 18/TypeScript + Huey + SQLAlchemy 2.x のモダンスタックで構築され、**非同期の章生成パイプライン**と**作品データ一式の ZIP エクスポート**を提供します。

![AutoNovel デモ](docs/demo.gif)

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/react-18-61dafb)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](#ライセンス)

---

## 目次

- [概要](#概要)
- [特徴](#特徴)
- [アーキテクチャ](#アーキテクチャ)
- [ディレクトリ構成](#ディレクトリ構成)
- [必要環境](#必要環境)
- [クイックスタート](#クイックスタート)
  - [ワンクリック起動 (Windows バッチ)](#ワンクリック起動-windows-バッチ)
  - [Docker Compose 起動](#docker-compose-起動)
  - [ローカル手動起動 (Windows PowerShell)](#ローカル手動起動-windows-powershell)
- [かんたんモードの使い方](#かんたんモードの使い方)
- [開発ワークフロー](#開発ワークフロー)
- [API エンドポイント](#api-エンドポイント)
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

## 概要

AutoNovel は、小説生成の**オーケストレーション基盤**を完成させたプロダクトです。フロントエンドからのリクエストを受けると、バックエンドは生成ジョブを Huey キューへ非同期投入し、ワーカーが処理した結果を DB へ永続化、フロントエンドはステータスをポーリングして受け取ります。最終的に作品（本文・キャラクター/世界観設定・プロット・JSON ダンプ）を 1 つの ZIP にまとめて即ダウンロードできます。

> **現在の実装ステータス（ご留意）**
> 生成パイプライン全体（キュー投入 → 非同期実行 → 永続化 → ステータスポーリング → エクスポート）は本番相当に動作しますが、**実際の本文を生成する LLM アダプタはプラグイン式のスタブ**です。`src/backend/routers/easy_mode.py` の `generate_with_llm()` は現在 `NotImplementedError` を送出する設計となっており、ここに実際の LLM プロバイダ呼び出しを実装することで本格生成が有効になります。ZIP エクスポートはフォールバック・データでも常に成功する仕様のため、LLM 未実装でも UI の全体フローを確認できます。

---

## 特徴

- ✨ **かんたんモード**: ジャンル・主人公設定・冒頭文を入力するだけで次章を生成。Huey タスクキューで非同期実行し、ステータスポーリングで結果を取得。
- 📦 **ZIP エクスポート**: 作品本文・キャラクター/世界観設定・プロット・JSON ダンプを 1 つの ZIP アーカイブにまとめて即ダウンロード（`book_id` 不在時もフォールバックで生成）。
- 🧱 **モダンスタック**: FastAPI (async) + SQLAlchemy 2.x + Huey (Redis/SQLite バックエンド切替可) + React 18 + Vite + TypeScript (strict)。
- 🧪 **テスト駆動**: pytest (`asyncio_mode=auto`) + Vitest。`real_db_manager` フィクスチャで実 DB セッションを用いた統合テストを実装。
- 🔍 **品質ゲート**: ruff (lint/format) + mypy (strict) + OpenAPI スキーマ生成・差分検知を CI で実施。
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
                            generate_chapter_task()
                            (LLM アダプタ呼出 → DB 永続化 → task クリーンアップ)
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
│   │   ├── server.py              # FastAPI アプリ + lifespan + /health /metrics
│   │   ├── observability.py       # ヘルスチェック・軽量メトリクスカウンタ
│   │   ├── logging_config.py      # structlog 風の JSON / テキストログ設定
│   │   ├── database/
│   │   │   ├── __init__.py        # engine, SessionLocal, init_db()
│   │   │   └── repository.py      # BookRepository (Task/Book/Chapter/...)
│   │   ├── routers/
│   │   │   └── easy_mode.py       # /easy_mode/* エンドポイント + generate_with_llm スタブ
│   │   ├── tasks/
│   │   │   ├── huey.py            # Huey インスタンス (sqlite/redis 切替)
│   │   │   └── generation_tasks.py# generate_chapter_task
│   ├── models/                    # SQLAlchemy モデル + Pydantic スキーマ
│   └── services/                  # digest_service / marketing (export)
├── frontend/
│   ├── src/
│   │   ├── App.tsx                # 2カラムレイアウト (Generate / Export)
│   │   ├── api/easyMode.ts        # API クライアント (fetch)
│   │   ├── components/            # GeneratePanel / ExportPanel
│   │   └── types/easyMode.ts
│   ├── Dockerfile                 # マルチステージ (dev / production nginx)
│   └── tests/                     # Vitest
├── tests/                         # pytest (backend) — conftest.py の real_db_manager
├── scripts/                       # release / smoke_test / generate_openapi / verify_all
├── docs/                          # api.md, openapi.json, demo.gif
├── Dockerfile / docker-compose.yml / docker-compose.prod.yml
├── Makefile / pyproject.toml / requirements*.txt
└── アプリ起動.bat / アプリ起動_ローカル.bat  # Windows 用起動バッチ
```

---

## 必要環境

- **Python** 3.12 以上
- **Node.js** 18 以上 (フロントエンドビルド・開発時)
- **Docker** 24 以上 + Docker Compose v2 (コンテナ実行時)
- Windows では PowerShell 7 推奨（付属バッチ利用可）

---

## クイックスタート

### ワンクリック起動 (Windows バッチ)

Windows 環境では、付属のバッチファイルをダブルクリックするだけで起動できます。

- **`アプリ起動.bat`** (Docker Compose 推奨): Backend / Worker / Frontend (dev) / PostgreSQL / Redis を一括起動。起動後 `http://localhost:5173` が開きます。
- **`アプリ起動_ローカル.bat`** (ローカル Python + Vite): ローカルの `.venv` と SQLite を利用して別ウィンドウで一括起動。事前に `py -m venv .venv`、`pip install -r requirements-dev.txt`、`cd frontend && npm install` を済ませてください。

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
# バックエンド API (内部)   : 8200 （postgres / redis は内部ネットワークのみ）
```

停止:

```powershell
docker compose down
# 本番環境の場合:
# docker compose -f docker-compose.prod.yml down
```

### ローカル手動起動 (Windows PowerShell)

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

## かんたんモードの使い方

1. **設定入力**: 左の「⚙️ 制作設定」で 作品ジャンル・レーティング / 主人公の名前 / 性格・特徴 / 特殊能力・スキル / 冒頭プロンプト を入力します。
2. **生成開始**: 「🪄 かんたん執筆開始」をクリック。バックエンドは `POST /easy_mode/generate` でタスクを Huey キューへ投入し、タスク ID を返します。
3. **ポーリング**: フロントエンドは `GET /easy_mode/status/{task_id}` を 1.5 秒間隔（最大 30 秒）でポーリングし、完了を待ちます。
4. **プレビュー**: 生成された章が右の「📖 執筆プレビュー」に表示され、次話への AI 提案（chips）も提示されます。
5. **納品**: 作品 ID（既定 `1`）を指定して「📦 納品パッケージ (ZIP) ダウンロード」をクリック。`GET /easy_mode/export/{book_id}` が本文・設定・プロット・JSON を含む ZIP を即ダウンロードします。

> ZIP には `01_本文.txt` / `02_キャラクター・世界観設定集.txt` / `03_プロット概要.txt` / `04_データダンプ.json` が含まれます。DB に該当作品がなくてもフォールバック・データで生成されるため、デモ用途でも常に動作します。

---

## 開発ワークフロー

主要な操作は `Makefile` または PowerShell スクリプトで実行できます。

| コマンド | 内容 |
|----------|------|
| `make install` | バックエンド依存をインストール (`pip install -r requirements-dev.txt -e .`) |
| `make dev` | フロントエンド依存も含めてセットアップ (`cd frontend && npm install`) |
| `make test` | バックエンドの pytest を実行 |
| `make lint` | ruff による静的解析 (`ruff check src tests`) |
| `make typecheck` | mypy による型チェック (`mypy src`) |
| `make openapi` | OpenAPI 仕様書を `docs/openapi.json` へ再生成 |
| `make frontend-test` | フロントエンドの Vitest を実行 |
| `make frontend-lint` | フロントエンドの ESLint + 型チェック |
| `make run` | バックエンド開発サーバー単体起動 (Port 8200) |
| `make dev-up` / `make dev-down` | Docker Compose 開発環境の起動 / 停止 |
| `make prod-up` / `make prod-down` | Docker Compose 本番構成の起動 / 停止 |
| `make verify` | lint + test + openapi + frontend-lint + frontend-test の全検証を一括実行 |
| `make clean` | キャッシュ (`__pycache__`, `.pytest_cache`) や一時 DB を削除 |

```powershell
# PowerShell スクリプトで全検証
.\scripts\verify_all.ps1
```

---

## API エンドポイント

Base URL (開発時): `http://localhost:8200`（Nginx 本番時: `http://localhost:8080`）

| Method | Path | 説明 |
|--------|------|------|
| `GET`  | `/health` | ヘルスチェック (DB / Huey 生存確認 + メトリクススナップショット。`status` は `ok` / `degraded`) |
| `GET`  | `/metrics` | プロセス内メトリクスカウンタのスナップショット |
| `POST` | `/easy_mode/generate` | 章生成タスクを Huey キューに投入し、suggestions に task ID を返却 |
| `GET`  | `/easy_mode/status/{task_id}` | タスクのステータス (`pending` / `completed` / `failed`) と生成結果を取得 |
| `GET`  | `/easy_mode/export/{book_id}` | 指定 `book_id` の ZIP エクスポート (`book_id >= 1`、違反時は 422) |

詳細なスキーマ定義とリクエスト/レスポンス例は [`docs/api.md`](docs/api.md) を参照してください。OpenAPI 仕様書は `py scripts/generate_openapi.py` で `docs/openapi.json` として生成できます。

---

## 環境変数

`.env.example` を参考に `.env` を作成してください。

| 変数 | 既定値 | 説明 |
|------|--------|------|
| `DATABASE_URL` | `sqlite:///./autonovel.db` | SQLAlchemy 接続 URL。PostgreSQL 利用時は `postgresql+psycopg2://...` |
| `REDIS_URL` | `redis://redis:6379/0` | Redis 接続 URL (`HUEY_BACKEND=redis` 時に使用) |
| `HUEY_BACKEND` | `sqlite` | `redis` または `sqlite`。開発・ローカル時は `sqlite` で Redis 不要 |
| `LOG_LEVEL` | `INFO` | ルートロガーのログレベル |
| `LOG_FORMAT` | `json` | ログ形式 (`json`: 構造化ログ、`text`: プレーンテキスト) |
| `APP_ENV` | `local` | デプロイ環境識別子 (全ログの `env` フィールドに付与) |
| `LOG_LEVEL_<NAME>` | (なし) | 特定ロガー `<NAME>` のレベル個別上書き (例: `LOG_LEVEL_HUEY=DEBUG`) |

---

## オブザーバビリティ

AutoNovel では運用信頼性と保守性を高めるため、構造化ロギング・詳細ヘルスチェック・軽量メトリクスを標準装備しています。

### 構造化ロギング

`src/backend/logging_config.py` により `python-json-logger` を用いた JSON ログ出力を提供します。全ログに `app` / `version` / `env` コンテキストが自動付与され、タスク投入・生成完了/失敗・エクスポート要求/成功・ステータスポーリング等の主要処理が構造化されます。

### ヘルスチェック (`GET /health`)

DB 接続確認 (`SELECT 1`) と Huey バックエンド (`len(huey)`) の生存確認を実施し、メトリクススナップショットを含むペイロードを返します。

- 全コンポーネント正常時: `"status": "ok"`
- いずれか異常時: `"status": "degraded"`（HTTP 200 を維持しつつ状態を明示）

### メトリクス (`GET /metrics`)

プロセス内カウンタ (`src/backend/observability.py`) により以下を追跡します（外部依存なしの最小実装、本格運用では Prometheus 等へ置換可能）:

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
- [`docs/openapi.json`](docs/openapi.json) — OpenAPI 3.1 仕様書（自動生成）
- [`CHANGELOG.md`](CHANGELOG.md) — 変更履歴 (Semantic Versioning 準拠)
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — 開発環境構築・コーディング規約・PR フロー
- [`SECURITY.md`](SECURITY.md) — セキュリティポリシー・脆弱性報告フロー

---

## セキュリティ

脆弱性を発見した場合は、GitHub の公開 Issue ではなく [SECURITY.md](SECURITY.md) に記載の手順に従い非公開レポートをお願いします。

---

## コントリビュート

コントリビューションを歓迎します。作業を開始する前に [CONTRIBUTING.md](CONTRIBUTING.md) をご確認ください。コミットメッセージは [Conventional Commits](https://www.conventionalcommits.org/) を推奨します。

---

## ライセンス

[MIT License](LICENSE)（詳細はリポジトリのライセンス表記を参照してください）。
