## 8. IF ルート分岐 API (`/api/branches`)

`src/easy_mode/phase3/if_routes.py` (1205 行) を製品の中核機能として公開する REST/WS API。

### 8.1 Branch 管理

| Method | Path | 機能 |
|--------|------|------|
| `POST` | `/api/branches/` | 新規ブランチ作成（`graph_json` 同梱可） |
| `GET` | `/api/branches/{book_id}` | 書籍の全ブランチをツリー順で取得 |
| `GET` | `/api/branches/{book_id}/graph?branch_id=` | IF グラフ JSON 取得 |
| `PUT` | `/api/branches/{book_id}/graph?branch_id=` | IF グラフ JSON 保存 |
| `POST` | `/api/branches/{book_id}/fork` | 既存ブランチから分岐作成 |
| `POST` | `/api/branches/{book_id}/merge` | 2 ブランチを MERGE ノードで合流 |
| `GET` | `/api/branches/{book_id}/nodes?branch_id=` | ノード一覧 |
| `POST` | `/api/branches/{book_id}/nodes?branch_id=` | ノード追加 |
| `DELETE` | `/api/branches/{book_id}/nodes/{node_id}?branch_id=` | ノード削除（孤立チェック） |
| `POST` | `/api/branches/{book_id}/editor/validate?branch_id=` | グラフ整合性検証（孤立/サイクル/参照切れ） |
| `GET` | `/api/branches/{book_id}/export` | 全ブランチを EPUB に変換し ZIP で返す |
| `GET` | `/api/branches/{book_id}/stats` | 統計（セッション数・完了数・総選択数・ユニークパス数） |
| `GET` | `/api/branches/{book_id}/choices` | 選択肢ごとの選択数 |

### 8.2 Player セッション（REST）

| Method | Path | 機能 |
|--------|------|------|
| `POST` | `/api/branches/play` | セッション開始（UUID 自動発行） |
| `GET` | `/api/branches/play/{session_id}/state` | 現状態（現在ノード / 利用可能choices / context） |
| `POST` | `/api/branches/play/{session_id}/choose` | 選択肢実行（version 楽観ロック） |
| `POST` | `/api/branches/play/{session_id}/save` | 現状態を save_points に追記 |
| `POST` | `/api/branches/play/{session_id}/load?index=` | セーブポイントから状態復元 |
| `POST` | `/api/branches/play/{session_id}/end` | セッション終了 |
| `GET` | `/api/branches/play/{session_id}/playthrough` | プレイスルー履歴 |

### 8.3 Player WebSocket

| Path | 機能 |
|------|------|
| `WS /api/branches/play/{session_id}/ws` | 双方向 IF プレイヤー |

クライアント → サーバー: `{"action": "choose"|"save"|"load"|"end", ...}`
サーバー → クライアント: `{"type": "state"|"error"|"closed", ...}`

### 8.4 互換性

- `branch_id=1` デフォルトは温存（Q5 方針）。`book.current_branch_id` を尊重しつつ、明示指定があれば優先
- `multimedia.py:125 generate_if_routes` は **並存**（Q1 方針）。削除しない
- Alembic マイグレーション `0015_add_branches_core` / `0016_add_branch_play_sessions` 適用が必要

### 8.5 詳細計画

`docs/implementation_plans/if_routes_productization.md` を参照。