# PostgreSQL 完全移行ガイド (Final Migration Guide)

## 1. 概要
本ドキュメントは、SQLite から PostgreSQL への完全移行を実施するための最終手順書である。フェーズ9のガイドである。

## 2. 移行前提条件
- PostgreSQL インスタンスが稼働しており、`kaku_hegemony_db` データベースおよびユーザーが作成されていること。
- `psycopg2-binary` および `asyncpg` がインストールされていること。
- `docs/postgresql_migration_plan.md` の計画に合意していること。

## 3. 移行手順

### ステップ 1: データベーススキーマの作成
PostgreSQL側でテーブルを作成する。
SQLAlchemy を使用している場合、以下のコマンドで PostgreSQL 接続先に対してスキーマを生成できる。

```bash
# 環境変数を PostgreSQL に設定
export DATABASE_URL="postgresql+asyncpg://postgres:password@localhost:5432/kaku_hegemony_db"
# Alembic でマイグレーションを実行（または SQLAlchemy の create_all を使用）
alembic upgrade head
```

### ステップ 2: データの移行
作成した移行スクリプトを実行してデータを転送する。

```bash
python scratch/migrate_to_pg.py
```

### ステップ 3: アプリケーション設定の変更
`.env` または `config/settings.toml` 等の接続文字列を更新する。

**変更前:**
`DATABASE_URL=sqlite+aiosqlite:///i:/claude2/kaku_hegemony_v2.db`

**変更後:**
`DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/kaku_hegemony_db`

### ステップ 4: 動作確認
1. **API サーバー起動**: `fastapi` サーバーを起動し、データの読み書きが正常に行われるか確認。
2. **ワーカー起動**: `huey` ワーカーを起動し、バックグラウンドタスクが正常に動作することを確認。
3. **データ整合性確認**:
   - SQLite 側のレコード数と PostgreSQL 側のレコード数が一致しているか。
   - 複雑なクエリ（JOIN等）の結果が一致しているか。

## 4. ロールバックプラン
移行後に致命的な問題が発生した場合、以下の手順で SQLite に戻す。
1. アプリケーションを停止する。
2. `DATABASE_URL` を SQLite のパスに戻す。
3. アプリケーションを再起動する。

## 5. 完了定義
- すべてのテーブルのデータが移行され、アプリケーションが PostgreSQL 上でエラーなく動作すること。
- 同時書き込みが発生しても `database is locked` エラーが発生しないことが確認されること。
