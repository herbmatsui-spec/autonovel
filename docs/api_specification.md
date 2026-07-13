# API 仕様書 (API Specification)

本ドキュメントは、フロントエンド（Streamlit）とバックエンドの間の通信に使用される API スキーマを定義したものです。すべてのリクエストとレスポンスは JSON 形式でやり取りされます。

## 1. 共通レスポンス形式
すべての API エンドポイントは、基本的に以下の `BaseResponse` 構造を返します。

| フィールド | 型 | 説明 |
| :--- | :--- | :--- |
| `success` | boolean | リクエストが成功したかどうか |
| `error_message` | string (optional) | 失敗時のエラーメッセージ |
| `error_type` | string (optional) | エラーの分類 (例: `ValidationError`, `LLMError`) |

---

## 2. ドメインデータモデル (Schemas)

### 2.1 作品情報 (`BookSchema`)
作品の基本情報を管理します。

| フィールド | 型 | 説明 |
| :--- | :--- | :--- |
| `id` | integer | 作品の一意識別子 |
| `title` | string | 作品タイトル |
| `genre` | string | ジャンル |
| `concept` | string | 作品コンセプト |
| `synopsis` | string | あらすじ |
| `target_eps` | integer | 目標エピソード数 |
| `cumulative_stress` | float | 累積ストレス値 |
| `created_at` | datetime | 作成日時 |

### 2.2 プロット情報 (`PlotSchema`)
各エピソードの構成案を管理します。

| フィールド | 型 | 説明 |
| :--- | :--- | :--- |
| `ep_num` | integer | エピソード番号 |
| `title` | string | プロットタイトル |
| `summary` | string | プロット概要 |
| `detailed_blueprint` | string | 詳細な設計図 |
| `tension` | float | 緊張度 (0-100) |
| `is_catharsis` | boolean | カタルシス発生エピソードか |
| `status` | string | 状態 (`open`, `closed`) |

### 2.3 本文情報 (`ChapterSchema`)
生成された小説本文を管理します。

| フィールド | 型 | 説明 |
| :--- | :--- | :--- |
| `ep_num` | integer | エピソード番号 |
| `title` | string | 章タイトル |
| `content` | string | 本文テキスト |
| `summary` | string | 内容要約 |
| `killer_phrase` | string | キラーフレーズ |
| `ai_insight` | string | AIによる分析・洞察 |
| `world_state` | object | 世界観の状態遷移データ |
| `trinity_review_log` | object | 三位一体レビューログ |
| `created_at` | datetime | 作成日時 |

### 2.4 世界観設定 (`BibleSchema`)
作品の共通設定（バイブル）を管理します。

| フィールド | 型 | 説明 |
| :--- | :--- | :--- |
| `id` | integer | バイブルID |
| `book_id` | integer | 紐づく作品ID |
| `settings` | object | 設定定義データ |
| `revealed` | object | 読者に開示済みの設定 |
| `version` | integer | バージョン番号 |

---

## 3. ワークフロー・タスク管理

### 3.1 タスクステータス (`TaskStatusSchema`)
非同期処理の進捗を追跡するためのモデルです。

| フィールド | 型 | 説明 |
| :--- | :--- | :--- |
| `task_id` | string | タスクの一意識別子 |
| `is_running` | boolean | 実行中かどうか |
| `current_step` | integer | 現在のステップ番号 |
| `total_steps` | integer | 全ステップ数 |
| `message` | string | 現在の処理内容 |
| `sub_message` | string | 詳細サブメッセージ |
| `trace_id` | string | トレーサビリティID |
| `streaming_text` | string | ストリーミング出力中のテキスト |
| `logs` | string[] | 実行ログ履歴 |
| `error` | string (optional) | 発生したエラー |
| `result_data` | any (optional) | 完了後の結果データ |
| `token_usage` | object | トークン使用量 (`prompt`, `completion`, `calls`) |
| `start_time` | float | 開始Unixタイムスタンプ |
