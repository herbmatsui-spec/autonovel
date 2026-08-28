# 実装計画: 成功レスポンスの統一フォーマット化 (api_success)

## 1. 背景・目的
現在、エラー時は `src/backend/error_handlers.py` 経由で `api_error()` に統一されているが、
成功時の POST レスポンスは `{"task_id": ...}` / `{"status": "ok", "message": ...}` / Pydantic モデル直接返却 などバラバラ。

すべての POST エンドポイントの成功レスポンスを `api_success()` の統一エンベロープにする。

統一フォーマット (`src/backend/response_helpers.api_success`):
```json
{ "success": true, "message": "…", "data": { … }, "timestamp": "2026-08-28T…Z" }
```

メリット:
- フロントエンドで `success` フラグで即判定可能
- エラー (`api_error`: `success:false, error_code, error_message, detail`) と対称になり、エラーハンドリングが一元化
- `message` により人間向けメッセージを標準保持

## 2. 実装方針

### バックエンド
- 各 router ファイルに `from src.backend.response_helpers import api_success` を追加。
- POST ハンドラの `return <payload>` を `return api_success(<payload>, "<メッセージ>")` に変更。
- `response_model=<Pydanticモデル>` が付与された POST エンドポイントから `response_model` を削除
  （エンベロープ dict を返すため。付けたままだと Pydantic モデル変換で `data` 等が落ちる）。
- ペイロードの種類に応じたルール:
  - タスク起動系: `api_success({"task_id": task_id}, "…を開始しました")`
  - 状態/メッセージ系(dict返却): 元の dict を `data` に保持 `api_success({"status":…, "message":…}, "…")`
  - Pydantic モデル返却: `api_success(result.model_dump(), "…")`  （`result` がモデル/リストの場合）

### フロントエンド (非破壊的適応)
`src/frontend/src/lib/apiClient.ts` の `request()` にて、レスポンス JSON が
エンベロープ (`success` 真偽値 + `data` キーを持つ object) の場合に `data` を取り出して返す
アンパック処理を追加。
- 既存の呼び出し側 (`api.ts`, `easyModeApi.ts`) は `response.data` をそのまま受け取る形になり変更不要。
- エラー時は既存の `api_error` エンベロープの `error_message` を利用して `ApiError` を throw（現状維持）。
- エンベロープでないレスポンス（GET 等、テストのモック `{task_id:…}`）はそのまま返すため、
  既存テスト (`api.test.ts`) も修正不要で通る。

## 3. 対象エンドポイント一覧 (計 39 = 30 routers + server.py 3 + ux_routes 6)

### src/backend/routers (30)
| ファイル | エンドポイント | 現在の返却 | message |
|---|---|---|---|
| easy_mode.py | /gacha | GachaResponse | ガチャ企画を生成しました |
| easy_mode.py | /digest | DigestResponse | ダイジェストを生成しました |
| easy_mode.py | /promote | PromotionResponse | 上級者モードへ引き継ぎました |
| marketing.py | /api/marketing/generate | {"task_id"} | マーケティング生成を開始しました |
| marketing.py | /api/marketing/export_package/{id} | {"message"} | 未実装のエンドポイントです |
| marketing.py | /api/marketing/analyze_style_dna | dict | 文体DNAを解析しました |
| issues.py | /{id}/resolve | {"status","message"} ×3 | 対応内容に応じたメッセージ |
| illustrations.py | /generate | res dict | 挿絵を生成しました |
| illustrations.py | /batch | res dict | 挿絵をバッチ生成しました |
| health.py | /api/continuity/check | ContinuityCheckResponse | 連続性チェックを実行しました |
| tasks.py | /{id}/stop | {"message"} ×2 | 停止要求を登録しました |
| episodes.py | /generate | {"task_id"} | エピソード生成を開始しました |
| episodes.py | /generate_candidates | {"task_id"} | エピソード候補生成を開始しました |
| episodes.py | /retry_failed | {"task_id"} | 失敗エピソード修復を開始しました |
| episodes.py | /chapters/import | {"task_id"} | 原稿インポートを開始しました |
| novel.py | /produce | ProduceNovelResponse | 小説制作を開始しました |
| narrative.py | /{b}/{br}/affinity/override | {"status","character_name","affinity_data"} | 好感度を上書きしました |
| narrative.py | /{b}/{br}/plot/rebuild | {"status", ...} | プロットを再構成しました |
| styles.py | /custom | {"status","message"} | カスタム文体を保存しました |
| styles.py | /fragments | {"status","message"} | 文体断片を登録しました |
| plots.py | /plan_generation | {"task_id"} | 企画生成を開始しました |
| plots.py | /expand | {"task_id"} | プロット展開を開始しました |
| plots.py | /expand_candidates | {"task_id"} | プロット候補生成を開始しました |
| plots.py | /rebuild | {"task_id"} | プロット再構築を開始しました |
| plots.py | /audit | dict | 企画監査を実行しました |
| prompt_versions.py | /api/prompt_versions/{id}/rollback | {"message"} | プロンプトバージョンをロールバックしました |
| patches.py | /{id}/approve | {"message"} | パッチを適用しました |
| patches.py | /{id}/reject | {"message"} | パッチを拒否しました |
| patches.py | /{id}/edit | {"message"} | パッチを更新しました |
| commercial.py | /run | partial env | 商用パイプラインを実行しました |

### src/backend/server.py (3) — 追加適用（同じ散在パターン）
- /api/refine_erotic → {"task_id"} → api_success
- /api/easy_mode/generate → {"task_id"} → api_success
- /api/critique/optimize → {"task_id"} → api_success

### src/api/routes/ux_routes.py (6) — 追加適用（router の POST）
- /api/ux/affinity/update → list[AffinityData] → api_success
- /api/ux/what-if → WhatIfResponse → api_success
- /api/ux/what-if/fork → BranchCreateResponse → api_success
- /api/ux/pacing → {"status",…} → api_success
- /api/ux/preference → {"status","preference"} → api_success
- /api/ux/hitl/resume → {"session_id",…} → api_success

## 4. 検証
- バックエンド: 変更ファイル `python -m py_compile` で構文チェック。
- フロントエンド: `npm run typecheck` / `npm test` (api.test.ts がエンベロープ非検知で通ることを確認)。
- 手動: タスク起動系が `{"success":true,"data":{"task_id":…}}` を返すことを確認。

## 5. リスク・注意
- `response_model` 削除により OpenAPI スキーマ上はエンベロープ型になる（意図通り）。
- GET エンドポイントは対象外（現状維持）。
- フロントエンドはアンパックにより呼び出し側の変更不要。PromotionResponse の `success` フィールドは
  `data` 内に維持されるため `EasyModeContainer.tsx` の `res.success` 判定は引き続き動作。
