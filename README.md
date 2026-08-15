# ⚔️ 覇権小説エンジン v3.3

**覇権小説エンジン**は、AI を使って小説を「かんたんに」「高品質に」書くためのツールです。

カクヨムなどの Web 小説サイトでランキング上位を狙える作品を、**ボタンひとつ**で自動生成します。

---

## ✨ 最近のアップデート (v3.3 - 2026-08-15)

### 🔧 バグ修正・安定性向上

| 修正項目 | 詳細 |
|----------|------|
| **BASE_DIR 定数修正** | `config/constants.py` の `BASE_DIR` を空文字列から `Path(__file__).parent.parent` に修正。プロンプトマネージャー等でのパス操作エラーを解消 |
| **erotic/vocabulary.py 定数追加** | 分割モジュール化時に欠落していた継続性トラッカー用定数（同意キーワード、スタミナ/心理状態、親密度レベル、ロケーション、状態遷移マトリクス等）を `src/agents/erotic/vocabulary.py` に完全移植 |
| **OpenTelemetry 1.43+ 互換化** | `src/core/otel_setup.py` を最新版 API に対応：`logs`→`_logs`、ログエクスポータをオプショナル化、`AlwaysOnSampler`→`ALWAYS_ON`、環境変数名修正、リソース属性削減 |
| **非同期テスト修正** | `tests/test_zamaa_generation.py`、`tests/test_zamaa_injection.py` に `@pytest.mark.asyncio` デコレータを追加 |

### 🎯 かんたんモード Phase 1-3 実装完了 (v3.2)

**ジャンル選択のみで、企画から完結・商業展開まで全自動生成**が可能になりました。

| 機能 | 詳細 |
|------|------|
| **9ジャンルプリセット** | ざまぁ・悪役令嬢・チート転生・スローライフ・ダンジョン運営・現代チート・TS転生・VRMMO・ループ |
| **SpiceGuard（尖り保護）** | 自動リライト時に「この話の命」となる尖り要素（独自比喩・キャラ声・伏線・感情描写・ジャンル専用語彙）をマーカーで保護・除去 |
| **LLMリトライ** | 失敗時自動リトライ（3回・指数バックオフ）で安定生成 |
| **人間レビューゲート** | 監査基準未達エピソードを自動検出・フラグ表示 |
| **ログ永続化** | JSONL形式でタスク単位ログ保存（`logs/easy_mode/`） |
| **IFルート生成** | ジャンル別の分岐グラフ（ざまぁカタルシス分岐・隠しルート・バッドエンド・真エンド等）を自動構築。不足ノードは自動補完 |
| **メディアミックス台本** | 漫画・音声ドラマ・動画用の展開台本をワンクリック生成 |
| **電子書籍書き出し** | EPUB / PDF / MOBI への変換（オプション依存ライブラリは未導入時も安全にスキップ） |
| **資産化パック** | 原本・IFルート・メディアミックス・電子書籍・プロモ素材・メタデータ・チェックサムを1つの ZIP に統合 |

---

## なにができる？

### ✍️ 小説を自動で書いてくれる

たとえば...

> **「なろう系の異世界ファンタジーを今日中に書きたい」**

→ ジャンルを選んで「生成」ボタンを押すだけ。数十秒〜数分で、企画からプロット（話の骨組み）、本文まですべて自動で作ります。

### 🎮 2 つのモード

| モード | こんな人に | 何ができるか |
|---|---|---|
| **かんたんモード** | とにかく今すぐ小説が欲しい人 | **ジャンル選んでボタンを押すだけ**。何も考えなくて OK。9ジャンルプリセット + SpiceGuard で「尖り」を守りながら全自動生成 |
| **⚙ 上級者モード** | こだわりたい人 | 各話のプロットを編集したり、文章の濃さを変えたり、納得いくまで修正できる |

### 📚 かんたんモード 対応ジャンル (9種)

| ジャンル | アイコン | キーワード | 尖り保護の要所 |
|---|---|---|---|
| ざまぁ・追放・無双 | 🗡️ | `ざまぁ` `無双` `圧倒的` `顔面蒼白` | カタルシス完結・悪党の絶望・戦力差 |
| 悪役令嬢・断罪回避 | 👑 | `フラグ回避` `隠しルート` `百合` `尊い` | フラグ折り・百合テンション・契約 |
| チート転生・即最強 | ⚡ | `スキル習得∞` `秒殺` `最適解` `デバッグ` | システム風味・効率自慢 |
| スローライフ・ほのぼの | 🌿 | `ふわふわ` `とろける` `ほっこり` `香り` | 五感豊かさ・日常儀式 |
| ダンジョン運営・経営 | 🏰 | `罠` `ギミック` `忠誠` `進化` `個性` | 罠クリエイティブ・モンスター個性 |
| 現代チート・都市伝説 | 📱 | `ルート権限` `パッチ` `実体化` `同期` | テックメタファー・現実干渉 |
| TS転生・百合・性別反転 | 🎀 | `可愛い` `美少女` `百合キス` `尊い` `永遠` | 性別ユーフォリア・百合親密 |
| VRMMO・ゲーム世界 | 🎮 | `フルダイブ` `同期` `実体化` `現実侵食` | 同期用語・現実滲み出し |
| ループ・時間逆行・真エンド | 🔄 | `周目` `真エンド` `全フラグ` `確率1` `必然` | ループカウント・収束・完全攻略 |

---

### 😤「ざまぁ」展開を自動で仕組む

面白い小説には「ストレス」と「解放」の波が大切です。

このツールは物語中の**読者のストレスを自動計算**して、「そろそろ気持ちよくなれる場面を入れよう」と判断。適切なタイミングで「ざまぁ」展開（無双・逆転）をねじ込んでくれます。

### 🔞 官能描写にも対応（オプトイン）

NSFW モードを ON にすれば、官能的な描写を含む小説も書けます。
オプトイン方式で、ON にしない限り生成されません。

---

## アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (React)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ EasyMode │  │ PlotsTab │  │ WriteTab │  │ AuditTab   │  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
│         │           │           │              │            │
│         └───────────┴───────────┴──────────────┘            │
│                         │                                     │
│              ┌──────────▼──────────┐                          │
│              │   API Client        │                          │
│              │ (Resilient HTTP)    │                          │
│              └──────────┬──────────┘                          │
└─────────────────────────┼─────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ Server   │  │ Engine   │  │ Agents   │  │ LLM Gateway│  │
│  └──────────┘  └──────────┘  └──────────┘  └────────────┘  │
│         │           │           │              │            │
│         └───────────┴───────────┴──────────────┘            │
│                         │                                     │
│         ┌───────────────┼───────────────┐                     │
│         ▼               ▼               ▼                     │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                │
│  │ SQLite   │    │ ChromaDB │    │  Redis   │                │
│  └──────────┘    └──────────┘    └──────────┘                │
└─────────────────────────────────────────────────────────────┘
```

### コアコンポーネント

| レイヤー | 技術スタック | 役割 |
|---|---|---|
| **Frontend** | React 18 + TypeScript + Vite + TailwindCSS | モダンな SPA UI、Zustand で状態管理 |
| **Backend** | FastAPI + Uvicorn | REST API、非同期処理、ヘルスチェック |
| **AI Orchestration** | LangGraph + Google Gemini | グラフベースの執筆パイプライン、リトライ/分岐制御 |
| **EasyMode Pipeline** | Python asyncio + SpiceGuard | ジャンル選択のみで全自動生成、尖り保護付きリライト |
| **Task Queue** | Huey + Redis | バックグラウンドジョブ管理、スケジューリング |
| **Persistence** | SQLite (dev) / PostgreSQL (prod) + Alembic | データ永続化、マイグレーション管理 |
| **Vector Store** | ChromaDB | RAG 用ベクトル検索、文脈記憶 |
 
 ### API クライアント (`src/infrastructure/api/api_client.py`)
 
 フロントエンド／バックエンド間の HTTP 通信を担うクライアント層。
 
 - **HTTP セマンティクス準拠**: `GET`/`DELETE`/`HEAD` は `params` を、`POST`/`PUT`/`PATCH` は `json` を使って引数を振り分け（同期エントリ `_request`）。
 - **同期／非同期の両対応**: テストやモック差し替えのため `client.request` がコルーチンを返す場合でも同期的に解決する（`_resolve_if_coroutine`）。
 - **接続の再利用**: 非同期 API は共有の `httpx.AsyncClient` を遅延生成・再利用し、終了時に `close_async_client()` でクローズ。
 - **リソース管理**: 同期クライアントは `get_client()` で共有・遅延生成され、アプリ終了時に `close_client()` で解放。
 - **堅牢なエラーハンドリング**: 接続エラー／HTTP エラー／予期せぬエラーを `APIException` に統一し、監査ログ (DI コンテナ経由) に記録。
 - **全メソッドに docstring と定数管理** (`DEFAULT_API_BASE_URL` / `SYNC_REQUEST_TIMEOUT` / `ASYNC_REQUEST_TIMEOUT`) を整備。
 
 ---

### API クライアント (`src/infrastructure/api/api_client.py`)

フロントエンド／バックエンド間の HTTP 通信を担うクライアント層。

- **HTTP セマンティクス準拠**: `GET`/`DELETE`/`HEAD` は `params` を、`POST`/`PUT`/`PATCH` は `json` を使って引数を振り分け（同期エントリ `_request`）。
- **同期／非同期の両対応**: テストやモック差し替えのため `client.request` がコルーチンを返す場合でも同期的に解決する（`_resolve_if_coroutine`）。
- **接続の再利用**: 非同期 API は共有の `httpx.AsyncClient` を遅延生成・再利用し、終了時に `close_async_client()` でクローズ。
- **リソース管理**: 同期クライアントは `get_client()` で共有・遅延生成され、アプリ終了時に `close_client()` で解放。
- **堅牢なエラーハンドリング**: 接続エラー／HTTP エラー／予期せぬエラーを `APIException` に統一し、監査ログ (DI コンテナ経由) に記録。
- **全メソッドに docstring と定数管理** (`DEFAULT_API_BASE_URL` / `SYNC_REQUEST_TIMEOUT` / `ASYNC_REQUEST_TIMEOUT`) を整備。

---

## かんたんモード パイプライン詳細

```
ユーザー操作          バックグラウンド処理
─────────            ────────────────
ジャンル選択 ──▶  1. Bible生成（世界観・キャラ・チート設定）
    │                2. プロット生成（テンション曲線×テンプレ展開）
    ▼                3. 各話ループ:
                       ├─ 執筆（Style DNA・フック・官能ルール注入）
                       ├─ 監査（95点未満なら）
                       ├─ SpiceGuard抽出（尖り要素検出）
                       ├─ マーカー注入（<<<SPICE:...>>>）
                       ├─ リライト（マーカー保護付き）
                       ├─ マーカー除去
                       └─ 最大3回繰り返し
                       4. シリーズ完結処理（タイトル・あらすじ・メタデータ）
                          ↓
    完了 ◀──────── 結果取得・人間レビュー表示（必要時）
```

### SpiceGuard（尖り保護システム）

自動リライトで面白さが平準化されないよう、**「この話の命」**となる要素を保護：

| 保護カテゴリ | 例 |
|---|---|
| **独自比喩** | 「まるで絶望の底から這い上がったかのように」 |
| **キャラ声** | 禁句・キャッチフレーズ（プリセット定義から） |
| **伏線・回収** | 「実は」「真実」「正体」「覚醒」 |
| **生々しい感情** | 「胸が締め付けられ」「背筋が凍る」 |
| **ジャンル専用語彙** | ざまぁ/無双/フラグ/百合/スキル∞/真エンド 等 |

**仕組み**: 抽出 → `<<<SPICE:type_pos>>>テキスト<<</SPICE>>>` マーカー注入 → LLMリライト（マーカー変更禁止指示） → マーカー除去

---

## 動かし方

### 方法 A: Docker でさくっと（おすすめ 🔰）

```bash
# 1. Google AI Studio で API キーを取得（無料）
# https://aistudio.google.com/app/apikey

# 2. 設定ファイルをコピーしてキーを書く
cp .env.example .env
# → .env ファイルを開いて GEMINI_API_KEY=取得したキー を追記

# 3. Docker を起動（開発用: フロントエンドは Vite dev server）
docker compose up --build

# または本番用ビルド（Nginx で静的配信）
docker compose --profile prod up --build
```

立ち上がったらブラウザで以下を開いてください：
- **開発モード**: http://localhost:5173 (Vite HMR 付き)
- **本番モード**: http://localhost:3000 (Nginx 静的配信)
- **バックエンド API**: http://localhost:8200/docs (Swagger UI)

### 方法 B: 手動で起動する（開発者向け）

```bash
# 1. 依存ライブラリを入れる
pip install -r requirements.txt

# 2. フロントエンド依存関係
cd frontend && npm install && cd ..

# 3. 環境変数を設定
export GEMINI_API_KEY="ここにAPIキーを入力"
export PYTHONPATH="$(pwd)"

# 4. バックエンド起動
uvicorn src.backend.server:app --host 127.0.0.1 --port 8200 --reload

# 5. （別のターミナルで）作業キュー起動
python -m huey.bin.huey_consumer src.backend.tasks.huey

# 6. （さらに別のターミナルで）フロントエンド起動
cd frontend && npm run dev
```

これで以下にアクセスできます：
- フロントエンド: **http://localhost:5173**
- バックエンド API: **http://localhost:8200/docs**

### 必要なもの

| 必須/任意 | 何に使うか |
|---|---|
| **必須** Python 3.12 以上 | バックエンド実行に必要 |
| **必須** Node.js 22 以上 | フロントエンドビルドに必要 |
| **必須** Gemini API キー | AI に小説を書かせるのに必要（Google AI Studio で無料取得可） |
| **任意** Docker / Docker Compose | 面倒な環境構築をスキップしたい人向け |
| **任意** Redis | 裏でジョブを管理する（Docker なら自動起動、ローカルなら別途必要） |

---

## 使い方の流れ

1. 起動するとブラウザにツールが表示されます
2. 左のサイドバーから「**かんたんモード**」か「**上級者モード**」を選びます
3. かんたんモードなら↓
   - 「お好みのジャンル」を選択
   - 「🎉 小説を生成」ボタンをクリック
   - しばらく待つと → 企画 → プロット → 本文 → 納品 まで自動で完了
4. 上級者モードなら↓
   - タブを切り替えながら各工程を細かく編集・調整できます

---

## しくみ（ざっくり）

### 執筆パイプライン（LangGraph ベース）

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ Planning│───▶│  Plot   │───▶│ Writing │───▶│  Audit  │───▶│ Polish  │
│  Agent  │    │  Agent  │    │  Agent  │    │ Agent   │    │ Agent   │
└─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘
     │            │            │            │            │
     ▼            ▼            ▼            ▼            ▼
  世界観設計   章構成・展開   本文生成      整合性検証    文体研磨
  キャラ設定   フック設計     シーン描写    伏線回収      NSFW調整
```

バックエンドは、**Huey** というワーカーが AI とのやり取りを管理し、長い処理が詰まらないようにします。データは自動的に **SQLite** ファイルに保存され、特別な設定は不要です。

---

## 🧪 テスト

```bash
# 全テスト実行
pytest

# かんたんモード Phase 1-3 統合テストのみ
pytest tests/test_phase1_preset_integration.py tests/test_phase2_pipeline_integration.py tests/test_phase3_asset_pack.py -v

# 詳細出力
pytest -xvs tests/
```

### テストカバレッジ (Phase 1-2)

| テスト種別 | 件数 | 内容 |
|---|---|---|
| **Phase 1: プリセット** | 17 | 全ジャンル存在確認・ローダー検証・UIインポート |
| **Phase 2: パイプライン** | 20 | SpiceGuard・設定・統合・E2E（フルラン・低スコア・尖り保護・キャンセル） |
| **Phase 3: 資産化** | 25 | IFルート・メディアミックス・電子書籍・資産化パック・統合 |
| **合計** | **62** | 全件通過 ✅ |

---

## 📊 監視・メトリクス

### ヘルスチェック (`/health`)

システム全体の健全性を確認するエンドポイント。以下のコンポーネントを並列チェックします：

| コンポーネント | チェック内容 |
|--------------|-------------|
| **Database** | SQLAlchemy 接続プールから接続取得 + `SELECT 1` 実行、レイテンシ測定 |
| **Redis** | `PING` + `INFO clients` で接続数確認 |
| **ChromaDB** | `heartbeat()` + コレクション一覧取得 |
| **LLM Gateway** | 軽量テスト生成（1 token）で API 疎通確認 |
| **Worker (Huey)** | バックエンド種類（Redis/SQLite）+ キュー深度 |

**レスポンス例**:
```json
{
  "status": "ok",
  "version": "3.0.0",
  "timestamp": "2026-08-08T01:44:30Z",
  "checks": {
    "database": {"status": "ok", "latency_ms": 12.3, "details": "pool=5/10", "error": ""},
    "redis": {"status": "ok", "latency_ms": 3.1, "details": "connected_clients=5", "error": ""},
    "chromadb": {"status": "ok", "latency_ms": 8.5, "details": "collections=3", "error": ""},
    "llm_gateway": {"status": "ok", "latency_ms": 245.0, "details": "model=gemini-3.5-flash-lite, response_len=4", "error": ""},
    "worker": {"status": "ok", "latency_ms": null, "details": "huey_backend=redis, queue_depth=0", "error": ""}
  }
}
```

**総合ステータス判定**:
- 全 `ok` → `ok`
- いずれか `degraded` → `degraded`
- いずれか `error` → `unhealthy`
- `not_configured` は警告だが全体を unhealthy にはしない

### Prometheus メトリクス (`/metrics`)

Prometheus 形式でメトリクスを公開。Grafana 等で可視化可能。

#### 標準 HTTP メトリクス
| メトリクス名 | タイプ | ラベル | 説明 |
|-------------|--------|--------|------|
| `http_requests_total` | Counter | method, path, status | HTTP リクエスト総数 |
| `http_request_duration_seconds` | Histogram | method, path | リクエストレイテンシ |
| `http_requests_in_progress` | Gauge | method, path | 進行中リクエスト数 |

#### アプリケーション固有メトリクス
| メトリクス名 | タイプ | ラベル | 説明 |
|-------------|--------|--------|------|
| `novel_generation_tasks_total` | Counter | workflow_type, status | 生成タスク総数 (started/completed/failed) |
| `novel_generation_duration_seconds` | Histogram | workflow_type | 生成完了までの所要時間 |
| `llm_api_calls_total` | Counter | model, status | LLM API 呼び出し数 (success/error/timeout) |
| `llm_api_tokens_total` | Counter | model, type | 使用トークン数 (prompt/completion) |
| `db_pool_connections_active` | Gauge | - | DB 接続プール使用中数 |
| `db_pool_connections_idle` | Gauge | - | DB 接続プールアイドル数 |
| `huey_queue_depth` | Gauge | - | Huey キュー深度 |
| `huey_tasks_processed_total` | Counter | status | 処理済みタスク数 (success/error/retry) |
| `chromadb_collections` | Gauge | - | ChromaDB コレクション数 |
| `redis_connected_clients` | Gauge | - | Redis 接続クライアント数 |

### 環境変数

| 変数名 | 説明 | デフォルト |
|--------|------|-----------|
| `KAKU_HEALTH_CHECK_LLM` | LLM ヘルスチェックを無効化 (`false` で無効) | `true` |

---

## 🙋 よくある質問

**Q: データはどこに保存されますか？**

A: 開発用は SQLite（`storage/app.db`）、本番は PostgreSQL に自動保存されます。Docker ならボリュームマウントで永続化されます。

**Q: 小説の権利はどうなりますか？**

A: あなたの API キーで生成された小説は、あなたのものです。利用規約の詳細は Google Gemini API の公式ドキュメントをご確認ください。

**Q: NSFW モードは大丈夫ですか？**

A: デフォルトでは OFF になっており、ON にしない限り官能描写は生成されません。ON にする際も同意確認があります。

**Q: React 版と Streamlit 版の違いは？**

A: Streamlit 版は廃止済みです。現在は React + TypeScript 製のモダンなフロントエンド（`frontend/`）がメインです。詳細は [ADR-0003](docs/adr/0003-streamlit-coexistence-strategy.md) を参照。

---

## （開発者向け）さらに詳しく

### ドキュメント

- [アーキテクチャ全体図](docs/architecture/overview.md)
- [プロジェクト構造](docs/architecture/structure.md)
- [AI オーケストレーション](docs/adr/0002-ai-orchestration-framework.md)
- [UI 設計方針](docs/adr/0003-streamlit-coexistence-strategy.md)
- [開発者ガイド](docs/guides/developer_manual.md)
- [デプロイメントガイド](docs/deployment_guide.md)

### 主要コマンド

```bash
# テスト実行
pytest                    # 全テスト
pytest -xvs tests/       # 詳細出力

# リンター・型チェック
ruff check .             # Ruff リンター
mypy src/                # 型チェック

# フロントエンド開発
cd frontend && npm run dev      # 開発サーバー
cd frontend && npm run build    # 本番ビルド
cd frontend && npm run lint     # ESLint

# データベースマイグレーション
alembic upgrade head     # マイグレーション適用
alembic revision --autogenerate -m "message"  # 新規リビジョン生成
```

### 環境変数

| 変数名 | 説明 | デフォルト |
|---|---|---|
| `GEMINI_API_KEY` | **必須** Google Gemini API キー | - |
| `PYTHONPATH` | Python モジュール検索パス | `/app` (Docker) |
| `DATABASE_URL` | DB 接続文字列 | `sqlite+aiosqlite:///storage/app.db` |
| `REDIS_URL` | Redis 接続文字列 | `redis://localhost:6379/0` |
| `LOG_LEVEL` | ログレベル | `INFO` |
| `CORS_ALLOWED_ORIGINS` | CORS 許可オリジン | `http://localhost:5173,http://localhost:3000` |
| `KAKU_HEALTH_CHECK_LLM` | LLM ヘルスチェックを無効化 (`false` で無効) | `true` |

---

## ライセンス

このプロジェクトは個人利用・研究目的で提供されています。商用利用の際は Google Gemini API の利用規約をご確認ください。

---

**Enjoy Writing!** ⚔️📖