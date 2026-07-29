# Security Policy

## Supported Versions

AutoNovel は個別の LTS バージョン運用を行わず、最新リリースのみをサポートします。

| Version | Supported          |
|---------|--------------------|
| 0.2.x   | ✅ 最新            |
| < 0.2   | ❌ サポート外      |

## 想定脅威モデル

AutoNovel はローカル・社内利用想定の小説生成エンジンです。以下は本プロジェクトのスコープ外です:

- 公開インターネットへの直接露出 (リバースプロキシや認証レイヤを別途配置してください)
- マルチテナント・ユーザ隔離
- LLM プロンプトインジェクション (生成結果は執筆補助として利用者が最終判断)

## 脆弱性報告

脆弱性を発見した場合は、公開 issue ではなく以下へ秘密で報告してください:

- リポジトリオーナーへ GitHub の "Security Advisories" 機能でプライベート advisory を作成
- またはセキュリティ連絡先 (リポジトリの README 参照) へ直接メール

報告後 5 営業日以内に受領確認、14 営業日以内に影響評価を返信します。

## 推奨デプロイメントプラクティス

本番運用に向けた最低限の推奨事項:

1. **DATABASE_URL** を SQLite ではなく PostgreSQL 等の管理 DB へ設定 ([`.env.example`](.env.example))
2. **HUEY_BACKEND** を `redis` に設定 (`HUEY_BACKEND_CLASS=redis` 相当)
3. `docker-compose.prod.yml` を使用し、バックエンド/ワーカー/フロントエンドを分離
4. ログは JSON 構造化ログ (`python-json-logger`) をファイルまたは集中ロギング基盤へ集約
5. `/easy_mode/export/{book_id}` のようなダウンロード系エンドポイントは認可レイヤで制御
6. §`Path(ge=1)`/§`Field(ge=1, le=10000)` 等の入力バリデーションは維持 (422 応答)

## 依存ライブラリの更新方針

- `requirements.txt` / `requirements-dev.txt` の依存は每月軽微に確認
- セキュリティ修正を含むパッチは即時取り込み (Dependabot 等で検知)
- メジャーアップデートは互換性テスト後に行う
