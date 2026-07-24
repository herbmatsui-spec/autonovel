# ⚔️ 覇権小説エンジン v3.0

「覇権小説エンジン v3.0」は、生成AI（Google Gemini）を活用し、Web小説プラットフォーム（カクヨム等）でランキング上位を狙える小説を自動・半自動で執筆・管理するための総合支援ツールです。

Python パッケージ名: `kaku-hegemony` (v3.0.0)

---

## 🧱 システム構成

本ツールは **FastAPI バックエンド** と **React UI** の 2 層構成です。重い生成処理は **Huey タスクワーカー**（Redis バックエンド、非導入時は SQLite へフォールバック）で非同期に実行されます。

| コンポーネント | 役割 | 既定ポート |
| --- | --- | --- |
| `src/backend/server.py` | FastAPI バックエンド（REST API + SSE 進捗配信） | `8200` |
| `frontend/` | React + TypeScript メイン UI | `3000` |
| `src/backend/tasks.py` | Huey タスクワーカー（非同期生成パイプライン） | — |
| `src/services/vector_store.py` | ChromaDB（RAG / 文体ラボ等のベクトル検索） | — |
| `src/backend/database/` | SQLAlchemy + Alembic マイグレーション（既定は SQLite） | — |

> **UI について**: メイン UI は `frontend/` の React + TypeScript (Vite) に移行済みです。旧 `streamlit_app/` は廃止予定です。

### ディレクトリ構成（抜粋）

```
src/
  backend/     FastAPI サーバー・ルーター・エンジン・ワーカー
  services/    LLM / ベクトルストア / ビジネスロジック
  agents/      AI オーケストレーション（ADR-0002）
  core/        監査可能性（Trace ID 等）・例外・共通ユーティリティ
  domain/      ドメインモデル
  llm/         Gemini クライアント・モデル選択
  infrastructure/  API クライアント・DI コンテナ
  models/      Pydantic スキーマ
  engine/      エンジン実装（プロンプト構築・ワークフロー）
  config/      設定・CORS
  prompts/     プロンプトテンプレート
  schemas/     データスキーマ定義
frontend/
  src/
    components/  UIコンポーネント
    store/      状態管理（Zustand）
    hooks/      UIロジック
    api.ts      バックエンドAPIクライアント
```

---

## 🚀 主な機能

### 1. 2つの動作モード
*   **かんたんモード（全自動）**: ジャンルを選択し、ボタンを1つ押すだけで、企画・プロット・執筆・納品までの全工程を完全自動で実行します。
*   **上級者モード（半自動・詳細調整）**: 各種パラメータを自在に制御しながら、章ごとの執筆やプロットの再構築、文体のカスタマイズなどを行うことができます。

### 2. ストレス感情曲線ループ（ざまぁ自動発動）
*   物語の展開に応じた「累積ストレス値（Tension）」をシステムが自動的に監視・計算します。
*   ストレスが一定値（例：65/100以上）に達すると、カタルシス（ざまぁ展開、主人公の無双、大逆転など）を自動的に発動させ、読者の購買欲求や感情の起伏をコントロールします。

### 3. 多彩なコントロールパネル
*   **企画立案**: ジャンル、メインターゲット、雰囲気（シリアス ↔ コミカル）、王道度（テンプレ重視 ↔ 芸術性重視）などの基本設定。
*   **プロット管理**: エピソードごとのあらすじ、登場キャラクター、目標の感情値の編集・閲覧。
*   **本文執筆**: 「情熱（Passion）」パラメータや「高解像度化（五感・心理描写の強化）」トグルを用いた、AIによる高品質な文章生成。
*   **監査・チケット管理**: 整合性のチェックやアンチパターンの検知を行い、未解決の課題を「チケット（Issue）」として管理・修正。
*   **文体ラボ**: キャラクター別の描写拡張テーマのカスタマイズ（RAG による類似文体検索を活用）。
*   **プロット再構築**: 途中でストーリーを変更したい場合に、それ以降のプロットを一貫性を保ったまま自動で再生成。

### 4. 官能描写モード（オプトイン方式）
*   **NSFW オプトイン**: サイドバーの「高度な詳細設定」から「🔞 NSFWモードを有効化」を ON にすると、初回のみ `nsfw_disclaimer.py` による同意確認ダイアログが表示されます。同意することで `session.config["enable_nsfw"] = True` となり、セーフティフィルターが緩和されます。
*   **強度・プラットフォーム制御**: 同意後は「🌡️ 官能描写の強度」（0:ほのぼの 〜 5:過激）や、カクヨム恋愛等の「📱 出力プラットフォーム」プリセットを選択できます。
*   **詳細エージェント設定**: 「🎬 官能エージェント詳細設定」から、映像パターン技術の適用、感覚ウェイト（触覚・嗅覚・聴覚・視線・呼吸・味覚）、ペーシング比率（Build / Peak / Afterglow）、品質パラメータ（比喩密度・心理描写深度）を細かく調整可能です。
*   **セーフティマニフェスト**: 生成時には `prompts/erotic/safety_manifest.py` のセーフティ・マニフェストが最優先でプロンプトに挿入され、同意の明示・未成年禁止・表現方針・余韻の義務が自動適用されます。
*   **バックエンド連携**: 官能描写の研磨は `/api/refine_erotic` エンドポイントを介して非同期で実行されます。

---

## 🛠️ 動作要件・セットアップ

### 1. 前提条件
*   **Python**: 3.10 以上（開発・CI は 3.12 で動作確認）。Docker 環境は Python 3.10 ベースです。
*   **Google Gemini API キー**: Google AI Studio 等から取得した有効な API キーが必要です（環境変数 `GEMINI_API_KEY`、または UI から入力）。
*   **（任意）Redis**: タスクワーカー用。未導入の場合は SQLite へフォールバックします。
*   **（任意）ChromaDB**: ベクトル検索（RAG）用。未導入の場合は機能が無効化されます。

### 2. Docker での起動（推奨）

`docker-compose.yml` にバックエンド（`:8200`）とフロントエンド（`:3000`）が定義されています。

```bash
# 任意: 環境変数を .env に用意（GEMINI_API_KEY など）
cp .env.example .env

docker compose up --build
```

起動後:
*   React UI: http://localhost:3000
*   Backend API:  http://localhost:8200 （`/docs` で Swagger UI を確認可）

### 3. ローカルでの起動

```bash
# 依存関係のインストール
pip install -r requirements.txt

# 環境変数（例）
export GEMINI_API_KEY="your-api-key"
export PYTHONPATH="$(pwd)"

# 1) バックエンド API
uvicorn src.backend.server:app --host 127.0.0.1 --port 8200

# 2) タスクワーカー (Huey)
python -m huey.bin.huey_consumer src.backend.tasks.huey

# 3) React UI
cd frontend && npm install --legacy-peer-deps && npm run dev
```

Windows の場合は `start_app.bat` を実行すると、上記プロセスをまとめて起動できます。

### 4. 環境変数

| 変数 | 説明 | 既定値 |
| --- | --- | --- |
| `GEMINI_API_KEY` | Google Gemini API キー | — |
| `DATABASE_URL` | DB 接続先（SQLAlchemy）。未指定時はローカル SQLite | `sqlite+aiosqlite:///./kaku_hegemony_v2.db` |
| `REDIS_URL` | Huey ワーカー用 Redis | `redis://localhost:6379/0`（未接続時は SQLite へフォールバック） |
| `CHROMA_URL` | ChromaDB エンドポイント（任意） | ローカル永続化 |
| `CORS_ALLOWED_ORIGINS` | 許可するオリジン（カンマ区切り / JSON 配列） | `http://localhost:5173` |
| `VITE_API_URL` | フロントエンドが参照するバックエンド URL | `http://localhost:8200/api` |

---

## 📖 基本的な使い方

### 💡 かんたんモードでサクッと書く
1.  サイドバーの「🎮 モード選択」で「🚀 かんたんモード」を選択します。
2.  「ジャンル」を選択し、「小説を生成」ボタンをクリックします。
3.  全自動パイプラインが走り、完了すると本文や成果物が出力されます。

### ⚙️ 上級者モードでこだわり抜く
1.  サイドバーで「⚙️ 上級者モード」を選択します。
2.  **企画立案**: 「📋 企画立案」タブで、各種スライダーやテキストボックスを入力し、「新しい作品の企画を生成」を実行します。
3.  **プロット調整**: 「📖 プロット管理」タブで、生成された各話のプロット（感情値やキャラクターの動き）をレビュー・修正します。
4.  **執筆**: 「✍️ 本文執筆」タブからエピソードを指定し、目標文字数や表現スタイル（情熱度など）を設定して「執筆開始」をクリックします。
5.  **監査と修正**: 「⚖️ 監査・チケット管理」タブで物語の矛盾点を検知し、必要に応じてプロットや本文を修正します。

### 🔞 NSFWモード（官能描写）を利用する
1.  サイドバーの「🛠️ コンテンツ制御設定」→「高度な詳細設定」を開きます。
2.  「🔞 NSFWモードを有効化」トグルを ON にします。
3.  初回は同意確認ダイアログが表示されるので、「同意して有効にする」をクリックします。
4.  強度スライダー（0〜5）やプラットフォームプリセット、必要に応じて「🎬 官能エージェント詳細設定」で感覚ウェイトやペーシングを調整します。
5.  通常通り執筆・生成を実行すると、官能描写が適用されます。OFF にすると設定がリセットされ、セーフティフィルターが元に戻ります。

---

## 🧪 テスト・品質管理

CI（`.github/workflows/ci.yml`）は lint（ruff）、型検査（mypy）、ユニット／統合テスト（pytest）を実行します。

```bash
# Lint / フォーマット確認
ruff check src/ tests/
ruff format --check .

# 型検査
mypy --config-file pyproject.toml src/

# テスト（ユニット / 統合）
pytest tests/unit -q
pytest tests/integration tests/test_vector_store_lifecycle.py -q
pytest tests/integration/test_erotic_refine_workflow.py -q
pytest tests/integration/test_erotic_full_pipeline.py -q
```

統合テストは ChromaDB（`chroma:0.5.5`）と Redis（`redis:7`）のコンテナを必要とします。詳細は CI ワークフローを参照してください。

---

## 📚 ドキュメント

*   アーキテクチャ方針: [docs/adr/0001-architecture-refactoring-policy.md](docs/adr/0001-architecture-refactoring-policy.md)
*   AI オーケストレーション: [docs/adr/0002-ai-orchestration-framework.md](docs/adr/0002-ai-orchestration-framework.md)
*   UI の共存・移行方針: [docs/adr/0003-streamlit-coexistence-strategy.md](docs/adr/0003-streamlit-coexistence-strategy.md)
*   プラグインシステム: [docs/adr/002-plugin-system.md](docs/adr/002-plugin-system.md)
*   エンジンの仲介レイヤ: [docs/adr/003-engine-mediator.md](docs/adr/003-engine-mediator.md)
## Refactoring Update (ADR-0004)
- Completed extraction of all core domain services (Planning, Writing, Critique, Bible, Tension).
- Implemented Dependency Injection container for better modularity and testability.
- Migrated domain workflows to a service-oriented architecture.
- Verified all core unit tests pass.

