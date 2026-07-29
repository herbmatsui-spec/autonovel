# AutoNovel Backend API Reference

AutoNovel バックエンドが提供する REST API のエンドポイント一覧・パラメータ・レスポンス例をまとめたドキュメント。

Base URL (開発時): `http://localhost:8200`

---

## 1. ヘルスチェック

### `GET /health`

サービス稼働確認用エンドポイント (Phase 5: Step 55-57 拡充版)。

`status` は全コンポーネント正常時に `ok`、いずれか異常時に `degraded`。
下位互換のため簡素な `{"status": "ok"}` を返していた旧版のスーパーセットとなっている。

**Response 200**

```json
{
  "status": "ok",
  "components": {
    "database": { "status": "ok", "latency_ms": 1.234 },
    "queue": { "status": "ok", "backend": "SqliteHuey" }
  },
  "metrics": {
    "tasks_enqueued": 0,
    "tasks_completed": 0,
    "tasks_failed": 0,
    "exports_attempted": 0,
    "exports_succeeded": 0,
    "health_checks": 1
  }
}
```

`components.database.status` / `components.queue.status` は実行環境によって
`ok` または `error` になる。`queue.backend` は `SqliteHuey` / `RedisHuey`。
`status` が `degraded` の場合でも HTTP 200 を返す (監視は `status` フィールドで判定)。

---

## 2. メトリクス

### `GET /metrics`

プロセス内メトリクスカウンタのスナップショットを返す (Step 58)。
外部依存なしの最小実装であり、本格運用では Prometheus 等への置換を想定。

**Response 200**

```json
{
  "tasks_enqueued": 3,
  "tasks_completed": 2,
  "tasks_failed": 1,
  "exports_attempted": 5,
  "exports_succeeded": 5,
  "health_checks": 12
}
```

| メトリクス名            | 更新タイミング                                   |
|------------------------|--------------------------------------------------|
| `tasks_enqueued`       | `POST /easy_mode/generate` がキュー投入に成功     |
| `tasks_completed`      | `generate_chapter_task` が成功                   |
| `tasks_failed`         | `generate_chapter_task` が例外で失敗             |
| `exports_attempted`    | `GET /easy_mode/export/{book_id}` 呼出時         |
| `exports_succeeded`    | エクスポート ZIP 生成成功時                       |
| `health_checks`        | `GET /health` 呼出時                             |

---

## 3. かんたんモード: 生成

### `POST /easy_mode/generate`

章生成タスクをキュー (Huey) に投入し、タスク ID を含む suggestions を返す。
実際の LLM 生成は非同期タスク (`generate_chapter_task`) 内で実行される。

**Request Body** (`EasyModeInput`)

| フールド              | 型                | 必須 | 制約                  | 既定値 |
|----------------------|-------------------|------|----------------------|--------|
| `chapter_history`     | `list[str]`       | ✗    |                      | `[]`   |
| `current_chapter`     | `str`             | ✗    |                      | `""`   |
| `character_params`   | `dict`            | ✗    |                      | `{}`   |
| `content_length_limit`| `int`             | ✗    | `ge=1, le=10000`     | `2000` |

**Request 例**

```json
{
  "current_chapter": "勇者は森を抜け、村にたどり着いた。",
  "chapter_history": ["第一話: 王都を飛び出す"],
  "character_params": { "name": "ルーク" },
  "content_length_limit": 2000
}
```

**Response 200** (`GenerationResponse`)

```json
{
  "output": "",
  "completion_time_ms": 0,
  "error": "",
  "suggestions": [
    "生成タスク ID: 12 を投入しました。ステータスを /easy_mode/status/12 で確認してください。"
  ]
}
```

**Response 422** (バリデーションエラー)

```json
{ "detail": [ { "msg": "Input should be greater than or equal to 1" } ] }
```

---

## 4. かんたんモード: ステータス参照

### `GET /easy_mode/status/{task_id}`

タスク ID の実行ステータスを返す。

**Path Parameter**

| 名前       | 型     | 制約       |
|-----------|--------|-----------|
| `task_id` | `str`  | 必須       |

**Response 200**

- 完了時:

  ```json
  { "task_id": "12", "status": "completed", "result": { "text": "...", "time": 1234 } }
  ```

- 進行中:

  ```json
  { "task_id": "12", "status": "pending" }
  ```

---

## 5. かんたんモード: エクスポート

### `GET /easy_mode/export/{book_id}`

指定した `book_id` の作品データを ZIP アーカイブとしてエクスポートする。
DB に作品が存在しない場合はフォールバックデータで ZIP を生成 (TC-12)。

**Path Parameter**

| 名前       | 型   | 制約        |
|-----------|------|------------|
| `book_id` | `int`| `Path(ge=1)` |

**Response 200** (binary, `application/zip`)

Headers:

- `Content-Disposition: attachment; filename="export_<book_id>.zip"; filename*=UTF-8''<quoted>`
- `Cache-Control: no-store`

**Response 422** (book_id < 1)

```json
{ "detail": [ { "msg": "Input should be greater than or equal to 1" } ] }
```

ZIP に含まれるファイル:

- `01_本文.txt`
- `02_キャラクター・世界観設定集.txt`
- `03_プロット概要.txt`
- `04_データダンプ.json`

---

## 6. 環境変数

| 変数名             | 既定値                          | 説明                                        |
|--------------------|---------------------------------|---------------------------------------------|
| `DATABASE_URL`     | `sqlite:///./autonovel.db`      | SQLAlchemy 接続 URL                         |
| `REDIS_URL`        | `redis://localhost:6379/0`      | Redis 接続 URL (Huey backend)               |
| `HUEY_BACKEND`     | `sqlite`                        | `sqlite` または `redis`                     |
| `LOG_LEVEL`        | `INFO`                          | ルートロガーのレベル                       |
| `LOG_FORMAT`      | `json`                          | `json` (python-json-logger) または `text`    |
| `APP_ENV`          | `local`                         | デプロイ環境識別子 (ログの `env` フィールド) |
| `LOG_LEVEL_<NAME>` | (なし)                          | 特定ロガー `<NAME>` のレベル上書き (例: `LOG_LEVEL_HUEY=DEBUG`) |

---

## 7. OpenAPI 自動生成

`scripts/generate_openapi.py` により、本 API の OpenAPI 3.1 仕様書を
`docs/openapi.json` としてエクスポート可能。

```powershell
py scripts/generate_openapi.py
```

CI では生成結果とリポジトリ上の `docs/openapi.json` との差分を検知し、
スキーマの drift を防止する。新しいエンドポイント・スキーマ変更時は
必ず再生成してコミットすること。
