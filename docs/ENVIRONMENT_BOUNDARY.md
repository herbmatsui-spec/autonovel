# 環境境界定義

## ローカル開発環境
- データベース: SQLite (`data/local.db`)
- キャッシュ: メモリベースまたはローカルファイル
- キュー: インメモリ（またはなし）
- サービス discovery: なし（シングルプロセス）
- ログレベル: DEBUG
- ホスト: `localhost:8000`

## 本番環境
- データベース: PostgreSQL + pgvector (ホスト: `db`, ポート: 5432)
- キャッシュ: Redis または memcached (環境変数で選択)
- キュー: Redis-backed RQ または Celery
- サービス discovery: Docker Compose ネットワークまたは Kubernetes
- ログレベル: INFO（エラー時は自動で DEBUG アップ）
- ホスト: `api.example.com` (HTTPS)
- TLS: Let's Encrypt または 内部 CA
- シークレット管理: Docker Secrets または 環境変数（実運用では Vault 推奨）