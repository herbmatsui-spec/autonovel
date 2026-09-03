# 設定バージョン管理・ロールバック手順

## 概要

本システムでは、世界観設定（Bible）の変更履歴を **SettingVersion**（完全スナップショット）と **SettingDelta**（差分）の二重構造で管理し、任意の時点へのロールバック・変更影響分析を可能にしています。

---

## データモデル

### SettingVersion（バージョン・スナップショット）
- 設定全体の完全コピーをバージョン番号付きで保存
- `book_id`, `version_number` で一意制約
- `base_version_id` で親バージョンを参照（ブランチ構造対応）
- `change_summary`: 変更内容の人間可読サマリー
- `created_by`: 変更者

### SettingDelta（差分レコード）
- 単一フィールドの変更差分
- `field_path`: ドット区切りパス（例: `world_rules.magic_system.mana_cost`）
- `old_value` / `new_value`: JSON文字列化された値
- `delta_type`: `MANUAL` / `AUTO_REPAIR` / `USER_CORRECTION`
- `source`: `user` / `audit_agent` / `bible_service`
- `merged_to_graphrag`: GraphRAG反映済みフラグ
- `patch_review_id`: レビュー経由の場合の参照

---

## バージョン作成のトリガー

| 操作 | バージョン作成 | 差分記録 |
|------|--------------|----------|
| ユーザーが Bible 画面で設定を手動編集 | ✅ | ✅ (MANUAL) |
| 監査レビュー承認時に設定修正適用 | ✅ | ✅ (USER_CORRECTION) |
| BibleService 自動修復（_audit_and_repair） | ✅ | ✅ (AUTO_REPAIR) |
| 企画生成時の初期保存 | ✅ (v1) | - |
| 明示的なスナップショット作成API呼び出し | ✅ | - |

---

## API 操作

### バージョン履歴取得
```bash
GET /api/patches/{book_id}/setting-versions
```
返却例：
```json
[
  {
    "id": 5,
    "book_id": 1,
    "version_number": 3,
    "snapshot_json": {"title": "Novel", "world_rules": {...}},
    "base_version_id": 2,
    "change_summary": "Manual change: world_rules.magic_system.mana_cost",
    "created_by": "editor1",
    "created_at": "2026-01-15T10:30:00"
  }
]
```

### 特定バージョン取得
```bash
GET /api/patches/{book_id}/setting-versions/{version_number}
```

### 差分履歴取得
```bash
GET /api/patches/{book_id}/setting-deltas?field_path=world_rules.magic_system.mana_cost
```

---

## ロールバック手順

### 方法1: Bible 管理画面から（推奨）

1. **Bible 設定画面** → 「バージョン履歴」タブを開く
2. 対象バージョンの「このバージョンに戻す」ボタンをクリック
3. 確認ダイアログで「はい」を選択
4. 自動的に以下が実行される：
   - 選択バージョンのスナップショットで Bible 上書き保存
   - 新しいバージョンとして記録（履歴は残る）
   - 差分レコード作成（delta_type: MANUAL）
   - GraphRAG への再インデックスキュー投入

### 方法2: API 経由

```bash
# 1. 対象バージョンを取得
GET /api/patches/1/setting-versions/3

# 2. Bible 更新（既存の Bible 更新 API を使用）
PUT /api/books/1/bible
Body: { 世界観設定全体 JSON }
```

※ 現状、専用の「ロールバック API」は未実装。Bible 更新 API 経由で実施し、バージョンは自動作成される。

### 方法3: 緊急時の直接 DB 操作（非推奨）

```sql
-- バックアップ取得
CREATE TABLE bibles_backup AS SELECT * FROM bibles WHERE book_id = 1;

-- 対象バージョンのスナップショットで上書き
UPDATE bibles
SET settings = (SELECT snapshot_json->>'bible' FROM setting_versions WHERE book_id = 1 AND version_number = 3),
    version = version + 1,
    last_updated = NOW()
WHERE book_id = 1;

-- 新バージョン記録
INSERT INTO setting_versions (book_id, version_number, snapshot_json, change_summary, created_by)
SELECT 1, (SELECT COALESCE(MAX(version_number),0)+1 FROM setting_versions WHERE book_id=1),
       snapshot_json, 'Emergency rollback to v3', 'admin'
FROM setting_versions WHERE book_id = 1 AND version_number = 3;
```

---

## 変更影響分析

### 未執筆話への影響検出（将来実装予定）

設定変更時に以下を自動解析：
1. 変更フィールドを参照している未執筆話のプロットを特定
2. 影響度スコア算出（高/中/低）
3. 警告通知をダッシュボードに表示

### 現在の影響確認方法

1. **差分履歴**で `field_path` を検索
2. 該当フィールドを使用しているプロンプト/テンプレートを `grep` 検索
3. 未執筆話のプロットブループリントを手動確認

---

## GraphRAG 同期

### 自動マージフロー
```
SettingDelta 作成
      │
      ▼
┌─────────────┐
│  バッチ処理  │ (1分ごと / 手動トリガー)
│ (GraphRAG   │
│  SyncService)│
└──────┬──────┘
       │
       ├──► ChromaDB: 旧ベクトル削除 → 新ベクトル追加
       │
       └──► Knowledge Graph: ノード属性 UPDATE
```

### 手動再インデックス
全設定を ChromaDB に再構築：
```python
from src.services.graphrag_sync_service import GraphRAGSyncService

service = GraphRAGSyncService(repo=repo, chroma_client=chroma)
await service.reindex_book_settings(book_id=1)
```

または API:
```bash
POST /api/admin/reindex-settings
Body: { "book_id": 1 }
```

### 同期状態確認
```bash
# 未マージ差分一覧
GET /api/patches/{book_id}/setting-deltas?merged_only=false

# マージ済みのみ
GET /api/patches/{book_id}/setting-deltas?merged_only=true
```

---

## 運用ベストプラクティス

### 1. 定期的なスナップショット作成
- 重要なマイルストーン（第1話完了、アーク完了等）で手動作成
- `change_summary` に「Arc 1 complete」「Pre-publishing snapshot」等を記載

### 2. 差分記録の活用
- `delta_type` でフィルタし、自動修復 vs 手動修正の割合を分析
- `source: audit_agent` が多い場合、企画段階での設定不足を示唆

### 3. バージョン番号の運用
- メインライン: 1, 2, 3... (連番)
- 実験的ブランチ: `base_version_id` で親を参照
- 本番適用時はメインラインにマージ（新バージョンとして記録）

### 4. クリーンアップ
- 古いバージョン（30世代以上前）はアーカイブ推奨
- `setting_deltas` は `merged_to_graphrag=true` で 90日以上経過したものをアーカイブ

---

## トラブルシューティング

| 症状 | 確認事項 | 対処 |
|------|----------|------|
| バージョンが作成されない | `repo.misc.create_setting_version` 呼び出しエラー | ログ確認、DB制約違反（ユニーク制約）確認 |
| 差分が GraphRAG に反映されない | `merged_to_graphrag=false` のまま | `merge_pending_deltas()` 手動実行、ChromaDB/KG接続確認 |
| ロールバック後に検索が古い値を返す | ChromaDB 再インデックス未実施 | `reindex_book_settings()` 実行 |
| バージョン番号が飛ぶ | 同時編集で競合 | 楽観的ロック（version番号チェック）導入検討 |

---

## 移行ガイド（既存データがある場合）

既存の `bibles` テーブルのみで運用していた場合：

```python
# 1. 現在の Bible を v1 として記録
from src.services.bible_service import WorldBibleGenerator

generator = WorldBibleGenerator(repo, llm, pm, debate, marketing, auditor)
await generator.create_setting_snapshot(
    book_id=1,
    change_summary="Initial version from existing bible",
    created_by="migration",
)

# 2. 過去の Bible 更新履歴がある場合は手動で v2, v3... を作成
# （履歴テーブルがない場合は v1 のみで開始）
```