# C4 アーキテクチャ図 - システムコンテキスト図

## 概要
覇権小説エンジン v3.3 のシステム全体像を示す。外部システム・ユーザーとの境界を明確化。

```mermaid
C4Context
    title システムコンテキスト図 - 覇権小説エンジン v3.3

    Person(user, "ユーザー", "Web UI / API 経由で小説生成をリクエスト")
    Person(admin, "管理者", "システム設定・監視・デプロイ")

    System_Boundary(b0, "覇権小説エンジン") {
        System(api, "API サーバー (FastAPI)", "REST API / WebSocket / 管理UI 提供")
        System(engine, "生成エンジン", "AI小説生成パイプライン実行")
        System(worker, "バックグラウンドワーカー (Huey)", "非同期タスク処理・レート制限管理")
    }

    System_Ext(gemini, "Google Gemini API", "LLM 生成 (Gemini 2.5 Pro / Flash)")
    System_Ext(openrouter, "OpenRouter / OpenAI 互換", "代替 LLM プロバイダー (Claude, GPT 等)")
    System_Ext(redis, "Redis", "キャッシュ・レート制限・セッション管理")
    System_Ext(db, "SQLite / PostgreSQL", "永続化ストレージ (小説データ・設定・ログ)")
    System_Ext(chromadb, "ChromaDB", "ベクトルストア (RAG・スタイル検索)")
    System_Ext(storage, "ローカルファイルストレージ", "生成済み小説・アセット・エクスポートファイル")

    Rel(user, api, "HTTPS / WebSocket", "小説生成リクエスト・進捗取得・結果ダウンロード")
    Rel(admin, api, "HTTPS", "システム設定・メトリクス確認・デプロイ管理")
    Rel(api, engine, "内部関数呼び出し / DI", "生成パイプライン起動・制御")
    Rel(api, worker, "Huey タスクキュー", "非同期ジョブ投入・進捗ポーリング")
    Rel(worker, engine, "内部関数呼び出し", "長時間実行タスクの実行")

    Rel(engine, gemini, "HTTPS (gRPC/REST)", "LLM 生成リクエスト (Gemini)")
    Rel(engine, openrouter, "HTTPS (OpenAI 互換)", "LLM 生成リクエスト (代替プロバイダー)")
    Rel(engine, redis, "Redis プロトコル", "キャッシュ取得・レート制限・セッション")
    Rel(engine, db, "SQL (async)", "小説データ・設定・Bible・プロット永続化")
    Rel(engine, chromadb, "gRPC/REST", "ベクトル検索 (RAG・スタイル DNA)")
    Rel(engine, storage, "ローカル FS", "生成済みテキスト・アセット・エクスポート保存")
```

## 境界の説明

| 境界 | 説明 | プロトコル |
|------|------|------------|
| ユーザー ↔ API | フロントエンド・CLI・外部連携からのアクセス | HTTPS, WebSocket |
| 管理者 ↔ API | 運用管理・設定変更・監視 | HTTPS |
| API ↔ Engine | 同期呼び出し・依存性注入 | Python インプロセス |
| API ↔ Worker | 非同期タスクキュー | Huey (SQLite/Redis バックエンド) |
| Engine ↔ 外部 LLM | 推論 API 呼び出し | HTTPS (gRPC/REST) |
| Engine ↔ Redis | キャッシュ・レート制限 | Redis RESP |
| Engine ↔ DB | 永続化 | SQL (aiosqlite/asyncpg) |
| Engine ↔ ChromaDB | ベクトル検索 | gRPC/HTTP |
| Engine ↔ Storage | ファイル I/O | ローカル FS / S3 互換 |

## 非機能要件への対応

- **可用性**: API はステートレス、Worker は冗長化可能
- **拡張性**: Engine は DI コンテナで依存性注入、プロバイダー切替容易
- **セキュリティ**: API キー認証・レート制限・CORS・セキュリティヘッダー
- **観測性**: OpenTelemetry 自動計装・Prometheus メトリクス・構造化ログ