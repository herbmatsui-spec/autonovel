# AutoNovel (オートノベル)
© 2026 HerbMatsui-spec. All rights reserved.

<div align="center">

**AI小説執筆・フォーマット・エクスポート支援ツール**

*FastAPI + React 18/TypeScript + Huey Task Queue + SQLAlchemy 2.0 + PostgreSQL 16 / Redis 7 / ChromaDB*

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![React 18](https://img.shields.io/badge/react-18.3-61dafb?logo=react&logoColor=black)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![ChromaDB](https://img.shields.io/badge/Vector-ChromaDB-FF6F61)](https://www.trychroma.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://www.docker.com/)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type Checked: mypy](https://img.shields.io/badge/type%20checked-mypy-blue)](https://mypy-lang.org/)
[![Vitest](https://img.shields.io/badge/tested_with-vitest-729B1B?logo=vitest&logoColor=white)](https://vitest.dev/)
[![Version](https://img.shields.io/badge/version-5.0.2-brightgreen?logo=semver)](https://github.com/herbmatsui-spec/autonovel/releases/tag/v5.0.2)

<br />

<p align="center">
  <img src="docs/demo.gif" alt="AutoNovel UI & Workflow Demo" width="900" style="border-radius: 10px; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
</p>

*▲ AutoNovel v5.0.2: デモアニメーション（説明用）。実際のAI生成品質・所要時間・外部サービス接続を示すものではありません。*

---

## 📋 何ができるのか？（概要）

AutoNovel は、AI を活用して Web 小説を **企画から執筆、校正、挿絵生成、納品まで** をサポートするツールです。プログラミングや AI の専門知識がなくても、ブラウザ上の簡単なフォームに情報を入力するだけで、小説の本文を生成し、設定集・プロット概要・データダンプをまとめた ZIP ファイルとしてダウンロードできます。

### 主な特徴

- **かんたんモード**：ジャンル・主人公設定だけで本文を生成
- **ワンクリック納品**：本文・設定・プロット・データを 1 つの ZIP にまとめて出力
- **上級者 Studio**：本文編集・次話展開提案・設定参照・矛盾診断・マルチメディア管理
- **投稿サイト整形**：なろう・カクヨム・アルファポリス向けに本文を自動変換
- **eBook エクスポート**：縦書き・EPUB 3 準拠の電子書籍ファイルを出力（外部依存あり）
- **マルチメディアアセット**：シーン画像・立ち絵・表紙（機能ガード付き・デモ用プレースホルダー）
- **GraphRAG ナレッジグラフ**（Apache AGE 未使用、pgvector/ChromaDB ベース）
- **品質監査**：静的ルール解析＋定性判定（LLM 未設定時は固定フォールバック）
- **設定の一元化**：LLM・画像・音声プロバイダの用途別切替

---

## 🚀 クイックスタート & 起動ガイド

### Windows ワンクリック起動（非推奨：既知の問題あり）

> **注意**: 現在の `アプリ起動.bat` および `アプリ起動_ローカル.bat` には既知の問題があります。開発環境では以下の手順を推奨します。

1. **`アプリ起動_ローカル.bat`** (軽量 / ローカル Python + SQLite 構成)
   - Docker を起動せず、ローカルの Python 仮想環境 (`.venv`) と SQLite で起動します。
   - ワーカープロセスは `--skip-migrations` フラグが正しく処理されません。手動で `python -m huey.bin.huey_consumer src.backend.tasks.huey.huey` を実行してください。
   - 起動完了後、ブラウザで `http://localhost:5173` が開きます。

### Docker Compose による起動（開発環境）

```powershell
# 環境変数を設定（例: .env ファイルを作成）
# 注意: .env.example の APP_VERSION は 4.9.0 のままです。実際のバージョンは 5.0.2 です。
# 必要に応じて LLM_PROVIDER=mock などを設定してください。

# コンテナのビルドと起動
docker compose up --build

# 起動後のアクセス先:
# フロントエンド UI : http://localhost:5173
# FastAPI Swagger UI: http://localhost:8200/docs
```

### ローカル手動環境構築（推奨）

```powershell
# ----------------------------------------------------
# 1. Python 仮想環境の作成と依存ライブラリのインストール
# ----------------------------------------------------
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -e ".[dev,rag]"

# ----------------------------------------------------
# 2. フロントエンドの依存ライブラリのインストール
# ----------------------------------------------------
cd frontend
npm install
cd ..

# ----------------------------------------------------
# 3. ターミナル 1: バックエンド API 起動 (SQLite モード)
# ----------------------------------------------------
$env:HUEY_BACKEND = "sqlite"
$env:DATABASE_URL = "sqlite:///./autonovel.db"
py -m uvicorn src.backend.server:app --reload --port 8200

# ----------------------------------------------------
# 4. ターミナル 2: Huey キューワーカー起動
# ----------------------------------------------------
$env:HUEY_BACKEND = "sqlite"
$env:DATABASE_URL = "sqlite:///./autonovel.db"
py -m huey.bin.huey_consumer src.backend.tasks.huey.huey

# ----------------------------------------------------
# 5. ターミナル 3: React フロントエンド開発サーバー起動
# ----------------------------------------------------
cd frontend
npm run dev
# ブラウザで http://localhost:5173 を開く
```

---

## 📖 実践操作マニュアル

### かんたんモード操作ステップ

```
[ステップ1: 設定入力] ──> [ステップ2: 本文生成] ──> [ステップ3: プレビュー&提案] ──> [ステップ4: 納品ZIP保存]
```

1. **基本設定と主人公プロファイルの入力**:
   - **ジャンル選択**: 「ハイファンタジー」「ダークファンタジー」「異世界転生」「現代ダンジョン」等から選択。
   - **主人公の名前**: 例 `アルト`
   - **性格・特徴**: 例 `熱血・仲間思い・冷静な判断力`
   - **特殊能力・スキル**: 例 `古代魔導剣術・時空間把握`
   - **冒頭 / 前話プロンプト**: 例 `薄暗い迷宮の最深部、少年アルトは封印されし古代の魔剣を抜いた。`

2. **生成の実行**:
   - 「🪄 かんたん執筆開始」ボタンをクリック。
   - レート制限チェックを通過後、非同期キューへタスクが投入され、プログレスバーが進捗を表示します。

3. **プレビューと次話展開の確認**:
   - 生成が完了すると、右側ペインに生成された本文が表示されます。
   - 下部に「💡 次話へのAI提案（3案）」が表示され、クリックすることで次話のプロンプトとして即座にセットできます。

4. **納品パッケージのダウンロード**:
   - 「📦 納品パッケージ (ZIP) ダウンロード」をクリックすると、`export_1.zip` が即座にダウンロードされます。

### 上級者 Studio の使い方

- 左ペイン: 主人公設定・世界観パラメータ・ジャンル設定の参照。
- 中央ペイン: 本文編集用リッチエディタ & 次の展開提案（Next Beats）。
- 右ペイン: GraphRAG 専属 AI 編集者（設定Q&A & リアルタイム矛盾診断）。
- タブ切替: エディタ / IF分岐ルート / 矛盾診断レポート / マルチメディア / 商用投稿。

---

## 📦 納品パッケージ (ZIP) の構造

ダウンロードされるZIPファイル（例: `export_1.zip`）は、以下の4つのファイルで構成されます：

```
export_1.zip
├── 01_本文.txt                      # 生成された本文テキスト
├── 02_キャラクター・世界観設定集.txt  # キャラクターシート ＆ 世界観設定 (Bible)
├── 03_プロット概要.txt              # 各話のあらすじ・1行要約・カタルシス一覧
└── 04_データダンプ.json             # 外部ツール・フロントエンド連携用完全JSON
```

---

## 🔧 設定パラメータ & 環境変数リファレンス

重要な環境変数は `.env.example` を参照してください。デフォルト値は `src/backend/config.py` で定義されています。

| 環境変数名 | 説明 |
|---|---|
| `LLM_PROVIDER` | 使用する推論エンジン (`mock`, `openai`, `gemini`, `claude`, `ollama`, `vllm`)。デフォルトは `mock`。 |
| `OPENAI_API_KEY` | OpenAI APIキー (`LLM_PROVIDER=openai` 時に必須) |
| `GEMINI_API_KEY` | Google Gemini APIキー (`LLM_PROVIDER=gemini` 時に必須) |
| `ANTHROPIC_API_KEY` | Anthropic APIキー (`LLM_PROVIDER=claude` 時に必須) |
| `IMAGE_PROVIDER` | 画像生成プロバイダ (`mock`, `dalle3`, `sd_webui`, `comfyui`) |
| `TTS_PROVIDER` | 音声合成プロバイダ (`mock`, `elevenlabs`) |
| `ENABLE_MULTIMEDIA` | マルチメディア生成を有効化 (`true`/`false`) |
| `ENABLE_AUDIO_SYNTH` | 音声合成を有効化 (`true`/`false`) |
| `HUEY_BACKEND` | タスクキュー種別 (`sqlite` または `redis`) |
| `DATABASE_URL` | データベース接続URL (`sqlite:///./autonovel.db` など) |

---

## ⚠️ トラブルシューティング & 既知の問題

| 現象 | 原因 | 対処法 |
|---|---|---|
| 進行バーが `pending` のまま完了しない | Huey ワーカープロセスが起動していないか、`--skip-migrations` フラグが正しく処理されない | ワーカーを手動で起動: `python -m huey.bin.huey_consumer src.backend.tasks.huey.huey` |
| 本番 Docker Compose の起動時にコンテナが即座に終了する | `.env` ファイルに `POSTGRES_PASSWORD` または `REDIS_PASSWORD` が設定されていない | `.env.example` をコピーして `.env` を作成し、強固なパスワードを設定してください |
| フロントエンドで「生成リクエストに失敗しました」または HTTP 429 が返る | 短時間に連続して執筆ボタンを押したため、IP単位のレートリミッターに抵触した | 60秒待機してから再試行してください |
| LLM 設定を変更しても反映されない | 設定を変えたら API と ワーカーを再起動する必要がある | API サーバーと Huey ワーカーを再起動してください |

---

## 📚 開発ワークフロー & コントリビューション

```bash
make help          # 利用可能なコマンド一覧を表示
make install       # バックエンドの依存ライブラリをインストール
make dev           # バックエンド・フロントエンドの全環境セットアップ
make test          # バックエンド pytest を実行
make lint          # Ruff による静的コード解析
make typecheck     # Mypy による型検査
make frontend-test # フロントエンド Vitest を実行
make frontend-lint # フロントエンド ESLint + 型検査を実行
make verify        # 全品質ゲートを一括実行 (PR前必須)
make clean         # キャッシュや一時DBファイルをクリーンアップ
```

品質計画・テスト網羅率プランは [TEST_COVERAGE_PLAN.md](TEST_COVERAGE_PLAN.md) を、パイプライン統合の将来計画は [PIPELINE_UNIFICATION_PLAN.md](PIPELINE_UNIFICATION_PLAN.md) を参照してください。

> **現行バージョン**: v5.0.2 (`pyproject.toml`, `frontend/package.json`, Docker イメージ `autonovel-backend:5.0.2` / `autonovel-frontend:5.0.2`)。直近のリリースノートは [CHANGELOG.md](CHANGELOG.md)。

---

<div align="center">
  <sub>Built with ❤️ for Novelists, Creators, and AI Engineers Worldwide.</sub>
</div>
</div>