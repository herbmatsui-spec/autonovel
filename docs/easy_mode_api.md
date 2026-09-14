# かんたんモード API 仕様書 (Easy Mode API Specification)

バージョン: 1.0
対象: `/easy_mode` エンドポイント群
ベースURL: `/easy_mode` (本番) / `/api/easy-mode` (開発環境のみ)

## 概要

かんたんモードは、AI小説生成を手軽に始められるよう設計された一連のエンドポイント群です。
以下の4つの主要フローを提供します:

1. **企画ガチャ (Gacha Pitch)** — 3つの物語案をランダム生成
2. **ダイジェスト (Quick Digest)** — 選択した企画から高速でプロット・第1話を生成
3. **対話型自動生成 (Interactive Writer)** — 章単位の本文生成
4. **昇格 (Producer Handoff)** — Studioモードへの引き継ぎ

---

## エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| `POST` | `/easy_mode/generate` | 章単位の非同期本文生成 |
| `GET` | `/easy_mode/generate/stream` | SSE リアルタイム生成 |
| `GET` | `/easy_mode/status/{task_id}` | タスクステータス確認 |
| `DELETE` | `/easy_mode/task/{task_id}` | タスクキャンセル |
| `POST` | `/easy_mode/gacha` | 3案ガチャ企画生成 |
| `POST` | `/easy_mode/digest` | ダイジェスト生成 |
| `POST` | `/easy_mode/promote` | Studioモード昇格 |
| `POST` | `/easy_mode/reverse-generate` | 逆算プロット生成 |
| `GET` | `/easy_mode/export/{book_id}` | 納品パッケージ (ZIP) エクスポート |
| `POST` | `/easy_mode/export-with-data` | カスタムデータ付き即時エクスポート |

---

## 1. POST /easy_mode/generate

章単位の対話型自動生成 [Interactive Writer]

### リクエストボディ

```json
{
  "chapter_history": ["前話の本文..."],
  "current_chapter": "現在執筆中の章テキスト",
  "character_params": {
    "name": "主人公の名前",
    "personality": "性格",
    "ability": "能力",
    "genre": "ファンタジー"
  },
  "content_length_limit": 2000,
  "target_episodes": 10,
  "llm_config": {
    "provider": "gemini",
    "api_key": "...",
    "model_name": "..."
  },
  "book_id": 1
}
```

### レスポンス (200 OK)

```json
{
  "task_id": "huey-task-uuid",
  "output": "処理ステータスメッセージ",
  "completion_time_ms": 123,
  "error": "",
  "suggestions": ["タスク ID: xxx 投稿されました。ステータスを /easy_mode/status/xxx で確認してください。"]
}
```

### エラー

| ステータス | 説明 |
|-----------|------|
| 422 | バリデーションエラー (例: `chapter_history` が list でない) |
| 429 | レートリミット超過 |
| 500 | サーバーエラー |

### バリデーション仕様

- `chapter_history`: `list[str]` (必須) — 文字列を渡すと Pydantic ValidationError (type=list_type)
- `content_length_limit`: `int` (1-10000)

---

## 2. POST /easy_mode/gacha

3案ガチャ企画生成 [Gacha Pitch]

### リクエストボディ

```json
{
  "genre": "fantasy",
  "keywords": ["magic", "sword"],
  "temperature": 0.7
}
```

### レスポンス (200 OK)

```json
{
  "request_id": "req-uuid",
  "plans": [
    {
      "plan_id": "p1",
      "plan_type": "royal",
      "title": "王道冒険譚",
      "logline": "勇者が魔王を倒す物語",
      "protagonist_summary": "正義感の強い青年",
      "charm_point": "熱い友情ドラマ"
    },
    { "plan_type": "curveball", "...": "変化球案" },
    { "plan_type": "dark", "...": "ダーク案" }
  ],
  "recommended_plan_id": "p1",
  "review_session_id": "..."
}
```

### 制約

- `plans` は **必ず3件** (min_length=3, max_length=3)
- `plan_type`: `royal` | `curveball` | `dark`

### エラー

| ステータス | 説明 |
|-----------|------|
| 400 | バリデーションエラー (ValueError) |
| 422 | Pydantic バリデーションエラー |
| 504 | LLM 生成タイムアウト |

---

## 3. POST /easy_mode/digest

ダイジェスト生成 [Quick Digest]

### リクエストボディ

```json
{
  "request_id": "req-uuid (gacha の request_id)",
  "selected_plan_id": "p1"
}
```

### レスポンス (200 OK)

```json
{
  "book_id": "book-uuid",
  "title": "王道冒険譚 ダイジェスト",
  "synopsis": "全体あらすじ...",
  "episode_1_text": "第1話: ...",
  "climax_preview_text": "クライマックス: ...",
  "status": "completed"
}
```

### エラー

| ステータス | 説明 |
|-----------|------|
| 400 | バリデーションエラー (無効な plan_id 等) |
| 422 | Pydantic バリデーションエラー |

---

## 4. POST /easy_mode/promote

上級者モード昇格 [Producer Handoff]

### リクエストボディ

```json
{
  "book_id": "book-uuid または int"
}
```

### レスポンス (200 OK)

```json
{
  "success": true,
  "redirect_url": "/studio/book_xxx",
  "state_token": "token-uuid"
}
```

### エラー

| ステータス | 説明 |
|-----------|------|
| 404 | 作品が見つからない (ValueError) |

---

## 5. POST /easy_mode/reverse-generate

逆算プロットビルダー用同期生成エンドポイント [Reverse Plot Builder]

### リクエストボディ

```json
{
  "answers": {
    "emotionalGoal": "triumph",
    "sacrifice": "peace",
    "coreConflict": "ideal_vs_reality",
    "openingHook": "isekai_awakening"
  },
  "targetEpisodes": 10,
  "genre": "ハイファンタジー (R15)",
  "llm_config": {}
}
```

### レスポンス (200 OK)

```json
{
  "arcs": [{ "...": "アーク情報" }],
  "episodes": [{ "...": "話数プロット" }],
  "catharsis_pattern": "...",
  "catharsisPattern": "..."
}
```

---

## 6. GET /easy_mode/status/{task_id}

タスクステータス確認

### レスポンス (200 OK)

```json
{
  "task_id": "abc123",
  "status": "pending | running | completed | failed",
  "result": { "output": "...", "zip_data": "...", "zip_filename": "..." }
}
```

### ステータス遷移

- `pending`: huey キューに結果なし
- `completed`: `{"output": "..."} 形式の結果あり
- `failed`: `{"error": "...", "text": "", "time": 0} 形式の結果あり

---

## 7. DELETE /easy_mode/task/{task_id}

タスクキャンセル

### レスポンス (200 OK)

```json
{
  "task_id": "task-123",
  "status": "cancelled"
}
```

---

## 8. GET /easy_mode/export/{book_id}

納品パッケージ (ZIP) エクスポート

### レスポンス (200 OK)

- Content-Type: `application/zip`
- Content-Disposition: `attachment; filename="export_1.zip"; filename*=UTF-8''...`
- Cache-Control: `no-store`
- DB に book が存在しない場合もフォールバックデータで ZIP を生成 (TC-12 仕様)

### ZIP 内構成

| ファイル | 内容 |
|---------|------|
| `01_本文.txt` | 全章本文 |
| `02_キャラクター・世界観設定集.txt` | キャラ・世界観設定 |
| `03_プロット概要.txt` | プロット一覧 |
| `04_データダンプ.json` | 機械可読 JSON |

---

## 9. POST /easy_mode/export-with-data

クライアントの最新ステートを反映した即時 ZIP エクスポート

### リクエスト

- Query: `?book_id=1`
- Body:

```json
{
  "title": "作品タイトル",
  "genre": "fantasy",
  "current_text": "本文...",
  "character": { "name": "主人公", "personality": "勇敢", "ability": "魔法" },
  "plots": [{ "ep_num": 1, "title": "第1話", "one_line_summary": "..." }]
}
```

### レスポンス (200 OK)

- Content-Type: `application/zip`
- `book_data` が提供された場合、DB のデータより優先して反映される

---

## メトリクス

| メトリクス名 | 説明 |
|-------------|------|
| `tasks_enqueued` | 生成タスク投入数 |
| `exports_attempted` | エクスポート試行数 |
| `exports_succeeded` | エクスポート成功数 |

---

## テスト

| テストファイル | 対象 |
|---------------|------|
| `tests/unit/test_easy_mode_router.py` | ルーター関数のユニットテスト (16 tests) |
| `tests/test_easy_mode_api.py` | API統合テスト (9 tests、E2Eフロー含む) |
| `tests/test_gacha_digest_service.py` | ガチャ・ダイジェストサービス単体テスト |
| `frontend/tests/integration/easyModeFlow.test.tsx` | フロントエンドAPIクライアント層テスト |

実行コマンド:

```bash
# バックエンド
python -m pytest tests/unit/test_easy_mode_router.py tests/test_easy_mode_api.py -v --no-cov

# フロントエンド
cd frontend && npx vitest run tests/integration/easyModeFlow.test.tsx
```
