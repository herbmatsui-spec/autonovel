# PostgreSQL 移行計画書 (Migration Plan)

## 1. 目的
現在の SQLite データベースから PostgreSQL への移行により、書き込みロック問題の根本的解決と、将来的なスケーラビリティ、データ整合性の向上を実現する。

## 2. 現状分析 (SQLite スキーマ)
- **総テーブル数**: 約 20 テーブル
- **主要テーブル**: `books`, `chapters`, `plot`, `characters`, `bible`, `outbox` など
- **データ型**:
    - `INTEGER` -> `INTEGER` / `BIGINT`
    - `VARCHAR` / `TEXT` -> `VARCHAR` / `TEXT`
    - `FLOAT` -> `DOUBLE PRECISION` / `NUMERIC`
    - `BOOLEAN` -> `BOOLEAN`
    - `DATETIME` (VARCHAR/DATETIME) -> `TIMESTAMP WITH TIME ZONE`
- **制約**:
    - 複合主キー (`chapters`, `character_arcs`, `plot` などで `branch_id`, `ep_num` 等の組み合わせ)
    - 外部キー制約 (論理的に存在し、移行時に明示的に定義する必要あり)

## 3. 移行戦略

### 3.1 移行アプローチ: 「オフライン移行」
データ量とダウンタイムの許容範囲に基づき、一度アプリケーションを停止してデータを移行するシンプルかつ安全なアプローチを採用する。

### 3.2 ステップ詳細

#### ステップ 1: PostgreSQL 環境構築
- インスタンスの構築 (Docker または Managed Service)
- データベースおよびユーザーの作成
- `asyncpg` ドライバの導入

#### ステップ 2: スキーマの定義 (DDL)
- SQLAlchemy のモデル定義を PostgreSQL 互換に調整
- SQLite 固有の型 (例: `BOOLEAN` の内部表現) を PostgreSQL の標準型に変換
- インデックスおよび制約の最適化

#### ステップ 3: データ抽出・変換・ロード (ETL)
- **抽出**: SQLite からデータを JSON または CSV 形式で抽出
- **変換**: 
    - 日付形式 (`VARCHAR` -> `ISO 8601` -> `TIMESTAMP`) の正規化
    - `NULL` 値の処理
- **ロード**: `psycopg2` または `asyncpg` を使用して PostgreSQL へインサート

#### ステップ 4: アプリケーションの接続先変更
- `config/settings.py` および環境変数 `DATABASE_URL` を更新
- `src/backend/database/core.py` の `DatabaseManager` を PostgreSQL 用に調整 (SQLAlchemy の `create_async_engine` 設定の変更)

#### ステップ 5: 検証と動作確認
- データ件数の整合性チェック
- 主要機能 (本作成、プロット生成、文字数カウント等) の動作確認
- 同時書き込み負荷テストの再実施 (PostgreSQL でのロック解消確認)

## 4. リスクと対策
- **型不整合**: SQLite は動的型付けであるため、移行時に型エラーが発生する可能性がある。
    - *対策*: 移行スクリプトにバリデーションを組み込み、エラーレコードをログ出力して個別に修正する。
- **パフォーマンス劣化**: インデックス設計が不適切だと、大規模データ時に遅延が発生する。
    - *対策*: `EXPLAIN ANALYZE` を用いてクエリを最適化する。
- **ダウンタイム**: 移行中のサービス停止。
    - *対策*: メンテナンス時間を設定し、バックアップを完全に取得した状態で実施する。

## 5. スケジュール (想定)
- スキーマ設計: 1日
- 移行スクリプト作成・テスト: 2日
- 本番移行・検証: 1日
