# C4 アーキテクチャ図 - コンテナ図

## 概要
覇権小説エンジン v3.3 のコンテナ（実行単位・デプロイ単位）レベルの構成を示す。

```mermaid
C4Container
    title コンテナ図 - 覇権小説エンジン v3.3

    Person(user, "ユーザー", "Web ブラウザ / API クライアント")
    Person(admin, "管理者", "運用管理")

    System_Boundary(api_boundary, "API サーバー (FastAPI)") {
        Container(api_app, "API アプリケーション", "Python 3.12 / FastAPI / Uvicorn", "REST API / WebSocket / OpenAPI ドキュメント / 管理UI")
        Container(middleware, "ミドルウェアスタック", "Python", "CORS / 認証 / レート制限 / トレースID / セキュリティヘッダー / メトリクス")
        Container(router_easy, "かんたんモード ルーター", "Python", "/api/easy_mode/* - 全自動生成エンドポイント")
        Container(router_adv, "上級者モード ルーター", "Python", "/api/advanced/* - 詳細制御エンドポイント")
        Container(router_legacy, "レガシー ルーター", "Python", "/api/legacy/* - 既存互換エンドポイント")
    }

    System_Boundary(engine_boundary, "生成エンジン (ライブラリ)") {
        Container(easy_pipeline, "かんたんモード パイプライン", "Python", "Bible→プロット→エピソード生成→監査→リライト→完結の全自動フロー")
        Container(adv_pipeline, "上級者モード パイプライン", "Python", "手動承認・分岐・IF ルート・メディアミックス連携")
        Container(engine_core, "エンジンコア (UltimateHegemonyEngine)", "Python", "LLMゲートウェイ・プロンプト管理・コンテキスト・SpiceGuard 統合")
        Container(llm_gateway, "LLM ゲートウェイ", "Python", "プロバイダー抽象化・セマンティックキャッシュ・リトライ・フォールバック")
        Container(spice_guard, "SpiceGuard", "Python", "尖り要素自動抽出・マーカー保護・リライトプロンプト生成")
    }

    System_Boundary(worker_boundary, "バックグラウンドワーカー") {
        Container(huey, "Huey タスクキュー", "Python / Huey", "非同期タスク実行・スケジューリング・リトライ・優先度制御")
        Container(rate_limiter, "レート制限クリーンアップ", "Python / asyncio", "定期的な IP 単位レート制限ストアの期限切れエントリ削除")
    }

    System_Boundary(data_boundary, "データストア") {
        ContainerDb(db, "SQLite / PostgreSQL", "SQL (aiosqlite/asyncpg)", "小説・エピソード・Bible・プロット・設定・ユーザー・ログ")
        ContainerDb(redis, "Redis", "Redis RESP", "キャッシュ・レート制限カウンター・セッション・Huey ブローカー")
        ContainerDb(chroma, "ChromaDB", "gRPC/HTTP", "ベクトル埋め込み (スタイル DNA・RAG・類似度検索)")
        ContainerDb(fs, "ローカルファイルシステム", "POSIX / S3 互換", "生成済み小説・画像・音声・EPUB/PDF/MOBI エクスポート")
    }

    System_Ext(gemini, "Google Gemini API", "LLM 生成 (Gemini 2.5 Pro/Flash)", "HTTPS")
    System_Ext(openrouter, "OpenRouter / OpenAI 互換", "代替 LLM (Claude, GPT, Llama 等)", "HTTPS")

    Rel(user, middleware, "HTTPS/WSS", "API リクエスト")
    Rel(admin, middleware, "HTTPS", "管理操作")
    Rel(middleware, router_easy, "内部ルーティング", "")
    Rel(middleware, router_adv, "内部ルーティング", "")
    Rel(middleware, router_legacy, "内部ルーティング", "")

    Rel(router_easy, easy_pipeline, "DI / 同期呼び出し", "生成開始")
    Rel(router_adv, adv_pipeline, "DI / 同期呼び出し", "生成開始")
    Rel(router_legacy, engine_core, "DI / 同期呼び出し", "レガシー互換")

    Rel(easy_pipeline, engine_core, "DI / 依存", "LLM・プロンプト・SpiceGuard 利用")
    Rel(adv_pipeline, engine_core, "DI / 依存", "LLM・プロンプト・SpiceGuard 利用")
    Rel(easy_pipeline, easy_pipeline, "内部", "Bible→Plot→Episode→Audit→Rewrite→Finalize")
    Rel(adv_pipeline, adv_pipeline, "内部", "手動承認・IF分岐・メディアミックス")

    Rel(engine_core, llm_gateway, "DI", "LLM 生成リクエスト")
    Rel(engine_core, spice_guard, "DI", "尖り保護・リライト")
    Rel(engine_core, middleware, "内部", "設定・レート制限参照")

    Rel(llm_gateway, gemini, "HTTPS (gRPC)", "Gemini 生成")
    Rel(llm_gateway, openrouter, "HTTPS (OpenAI 互換)", "代替 LLM 生成")

    Rel(easy_pipeline, db, "SQL (async)", "読み書き")
    Rel(adv_pipeline, db, "SQL (async)", "読み書き")
    Rel(engine_core, redis, "Redis RESP", "キャッシュ・レート制限")
    Rel(engine_core, chroma, "gRPC/HTTP", "ベクトル検索")
    Rel(easy_pipeline, fs, "FS I/O", "生成物保存")
    Rel(adv_pipeline, fs, "FS I/O", "生成物・アセット保存")

    Rel(router_easy, huey, "タスク投入", "非同期生成ジョブ")
    Rel(router_adv, huey, "タスク投入", "非同期生成ジョブ")
    Rel(huey, easy_pipeline, "タスク実行", "バックグラウンド生成")
    Rel(huey, adv_pipeline, "タスク実行", "バックグラウンド生成")
    Rel(huey, redis, "ブローカー", "タスクキュー永続化")
    Rel(huey, db, "SQL", "タスク結果永続化")
    Rel(rate_limiter, redis, "Redis RESP", "クリーンアップ")
```

## コンテナ詳細

| コンテナ | 技術スタック | 責務 | スケーリング |
|---------|-------------|------|-------------|
| API アプリケーション | FastAPI + Uvicorn | HTTP 終端・ルーティング・OpenAPI | 水平 (ステートレス) |
| ミドルウェアスタック | Starlette Middleware | 横断的関心事 (認証・CORS・レート制限・トレース) | - |
| かんたんモード ルーター | FastAPI Router | `/api/easy_mode/*` エンドポイント | - |
| 上級者モード ルーター | FastAPI Router | `/api/advanced/*` エンドポイント | - |
| レガシー ルーター | FastAPI Router | 互換性維持 | - |
| かんたんモード パイプライン | Python Library | 全自動生成フロー制御 | - |
| 上級者モード パイプライン | Python Library | 手動承認・分岐・メディアミックス | - |
| エンジンコア | Python Library | LLM・プロンプト・コンテキスト統合 | - |
| LLM ゲートウェイ | Python Library | プロバイダー抽象化・キャッシュ・リトライ | - |
| SpiceGuard | Python Library | 尖り保護・マーカー・リライトプロンプト | - |
| Huey タスクキュー | Huey + SQLite/Redis | 非同期タスク・スケジューリング | 垂直 (単一インスタンス推奨) |
| SQLite/PostgreSQL | aiosqlite/asyncpg | 永続化ストレージ | 読み取りレプリカで水平可 |
| Redis | redis-py | キャッシュ・レート制限・ブローカー | クラスタで水平可 |
| ChromaDB | chromadb-client | ベクトル検索 | シャーディングで水平可 |
| ファイルシステム | ローカル/S3 | 生成物・アセット保存 | オブジェクトストレージで水平可 |

## デプロイメント単位

```
┌─────────────────────────────────────┐
│  Kubernetes Deployment / Docker     │
│  ─────────────────────────────────  │
│  ├─ API Server (FastAPI) x N       │ ← 水平スケール
│  ├─ Huey Worker x M                │ ← タスク並列度制御
│  ├─ Redis (Cluster)                │ ← キャッシュ・キュー
│  ├─ PostgreSQL (Primary/Replica)   │ ← 読み取りスケール
│  ├─ ChromaDB (Cluster)             │ ← ベクトル検索スケール
│  └─ Object Storage (S3/MinIO)      │ ← 生成物ストレージ
└─────────────────────────────────────┘
```

## コンテナ間通信パターン

| From → To | パターン | プロトコル | 非同期/同期 |
|----------|---------|-----------|-------------|
| API → Engine | 同期呼び出し | インプロセス (DI) | 同期 |
| API → Huey | タスク投入 | 関数呼び出し | 非同期 (Fire & Forget) |
| Huey → Pipeline | タスク実行 | 関数呼び出し | 同期 (Worker 内) |
| Engine → LLM | API 呼び出し | HTTPS (gRPC/REST) | 同期 (タイムアウト付き) |
| Engine → Redis | コマンド | Redis RESP | 同期 (ミリ秒) |
| Engine → DB | クエリ | SQL (async) | 同期 |
| Engine → ChromaDB | ベクトル検索 | gRPC/HTTP | 同期 |
| Engine → FS | ファイル I/O | POSIX/S3 API | 同期/非同期 |