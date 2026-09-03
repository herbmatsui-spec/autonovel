# 実装計画: ユーザー向け矛盾レポート & 承認ワークフロー + 設定変更の差分マージ & 自動学習ループ

## 概要
既存の `AuditAgent` → `WritingAgent` 自動リトライフローに、**ユーザー確認・承認ステップ**を追加し、設定手動修正を **GraphRAG に自動反映・学習データ化** する仕組みを実装する。

---

## 対象ファイル・モジュール
- **Backend**: `src/agents/audit_agent.py`, `src/backend/workflows/writing_langgraph.py`, `src/services/bible_service.py`, `src/backend/database/models.py`, `src/backend/routers/patches.py`, `src/backend/routers/editor.py`
- **Frontend**: `frontend/src/components/editor/ConflictModal.tsx`, `frontend/src/components/editor/EditorialSidebar.tsx`, `frontend/src/api/editor.ts`
- **Database**: `bibles`, `audit_issues`, `pending_patches` への拡張、新テーブル `setting_deltas`, `setting_versions`, `patch_reviews`

---

## 18ステップ実装計画

### Phase 1: データモデル拡張 (Steps 1-4)

#### Step 1: PatchReview ステートマシン用 enum/モデル追加
**ファイル**: `src/backend/database/models.py`
- `PatchReviewStatus` enum: `GENERATED` → `UNDER_REVIEW` → `APPROVED` / `REJECTED` / `NEEDS_REVISION`
- `PatchReview` テーブル追加:
  - `id`, `book_id`, `ep_num`, `patch_type` (config/prompt/setting), `original_content`, `proposed_content`, `diff_json`
  - `status` (PatchReviewStatus), `reviewer_id`, `reviewed_at`, `review_comment`
  - `audit_issue_ids` (JSON配列: 関連する audit_issues 参照)
  - `learning_metadata` (JSON: ネガティブサンプルフラグ, 信頼度, パターンタグ)

#### Step 2: SettingDelta / SettingVersion モデル追加
**ファイル**: `src/backend/database/models.py`
- `SettingDelta` テーブル:
  - `id`, `book_id`, `field_path` (例: "world_rules.magic_system.mana_cost"), `old_value`, `new_value`
  - `delta_type` (MANUAL/AUTO_REPAIR/USER_CORRECTION), `source` (user/audit_agent/bible_service)
  - `merged_to_graphrag` (Boolean), `merged_at`, `created_at`
- `SettingVersion` テーブル:
  - `id`, `book_id`, `version_number`, `snapshot_json` (全設定の完全スナップショット)
  - `base_version_id` (親バージョン), `change_summary`, `created_at`, `created_by`

#### Step 3: AuditIssue にレビュー連携フィールド追加
**ファイル**: `src/backend/database/models.py`
- `AuditIssue` に追加:
  - `patch_review_id` (ForeignKey: PatchReview へのリンク)
  - `user_resolution` (USER_ACCEPTED/USER_REJECTED/USER_MODIFIED)
  - `resolved_at`, `resolved_by`

#### Step 4: Alembic マイグレーション生成・実行
**ファイル**: `alembic/versions/xxxx_add_patch_review_and_setting_version.py`
- 上記3テーブル + カラム追加のマイグレーション作成
- `alembic upgrade head` 実行確認

---

### Phase 2: バックエンド - レビューワークフロー実装 (Steps 5-9)

#### Step 5: AuditAgent にレビュー要求ロジック追加
**ファイル**: `src/agents/audit_agent.py`
- `run()` 修正: 全監査失敗時、即座に `WritingAgent` へリトライせず **PatchReview レコード作成** して `UNDER_REVIEW` 状態にする
- `audit_feedback` に `patch_review_id` 含めて返却
- `AgentResult.artifacts` に `requires_user_review: true`, `patch_review_id` 追加

#### Step 6: WritingLangGraph にレビュー待機ノード追加
**ファイル**: `src/backend/workflows/writing_langgraph.py`
- 新ノード `node_review_wait` 追加
- `route_after_audit` で失敗時 → `review_wait` に分岐
- `node_review_wait`: ポーリング or WebSocket で `PatchReview.status` 変化待機
  - `APPROVED` → `dogfeed` (続行)
  - `REJECTED` → `healing` (修復再試行)
  - `NEEDS_REVISION` → `drafting` (再執筆)
- タイムアウト設定 (デフォルト 24h) → 自動 `REJECTED` 扱い

#### Step 7: PatchReview CRUD API 実装
**ファイル**: `src/backend/routers/patches.py` (拡張)
- `GET /api/patches/{book_id}/reviews` - レビュー待ち一覧取得
- `GET /api/patches/reviews/{review_id}` - 詳細取得 (diff含む)
- `POST /api/patches/reviews/{review_id}/approve` - 承認
- `POST /api/patches/reviews/{review_id}/reject` - 差し戻し (コメント必須)
- `POST /api/patches/reviews/{review_id}/revise` - 修正案提示 (新しい proposed_content)

#### Step 8: 矛盾レポート詳細生成サービス
**ファイル**: `src/services/conflict_report_service.py` (新規)
- `generate_conflict_report(audit_issues, bible_snapshot)` → 構造化レポート
  - 矛盾カテゴリ別グルーピング (世界観/キャラクター/プロット/因果律)
  - 該当設定箇所の特定 (field_path, 現在値, 推奨値)
  - diff 形式での修正案生成 (unified diff / JSON patch)
  - 重要度スコアリング (critical/high/medium/low)

#### Step 9: EditorAssistService に「設定修正提案」機能追加
**ファイル**: `src/services/editor_assist_service.py`
- `propose_setting_fix(field_path, current_value, conflict_context)` → 推奨値 + 根拠
- GraphRAG (ChromaDB + Knowledge Graph) から類似修正履歴を検索し参考提示

---

### Phase 3: フロントエンド - 矛盾レポートパネル (Steps 10-13)

#### Step 10: ConflictReportPanel コンポーネント新規作成
**ファイル**: `frontend/src/components/editor/ConflictReportPanel.tsx`
- タブ構成: [矛盾一覧] [詳細diff] [承認アクション]
- 矛盾カード: アイコン(重要度), カテゴリ, 説明, 該当設定パス, 現行値/推奨値
- diff ビュー: `react-diff-viewer` または自作 unified diff 表示
- アクションボタン: [承認] [差し戻し+コメント] [修正案編集]

#### Step 11: EditorialSidebar にレビュー待ちバッジ・導線追加
**ファイル**: `frontend/src/components/editor/EditorialSidebar.tsx`
- サイドバー上部に「レビュー待ち: N 件」バッジ表示
- クリックで `ConflictReportPanel` をモーダル/ドロワー表示
- WebSocket / polling でリアルタイム更新

#### Step 12: API クライアント拡張
**ファイル**: `frontend/src/api/editor.ts` (または新規 `patchReviewApi.ts`)
- `fetchPendingReviews(bookId)`, `fetchReviewDetail(reviewId)`
- `approveReview(reviewId)`, `rejectReview(reviewId, comment)`, `reviseReview(reviewId, newContent)`

#### Step 13: 通知・リアルタイム同期
**ファイル**: `frontend/src/hooks/usePatchReviews.ts` (新規)
- `usePatchReviews(bookId)`: SWR / TanStack Query でポーリング (10秒間隔)
- WebSocket 対応時は `useWebSocketPatchReviews` に切替可能な設計

---

### Phase 4: 設定変更差分マージ & 学習ループ (Steps 14-18)

#### Step 14: BibleService に SettingDelta 記録フック追加
**ファイル**: `src/services/bible_service.py`
- `_apply_manual_setting_change(field_path, old_value, new_value, source="user")` メソッド追加
- `SettingDelta` レコード作成 + `SettingVersion` スナップショット作成 (バージョン番号インクリメント)
- 既存 `save_full_world_bible` 経由の保存時に自動フック

#### Step 15: GraphRAG への自動マージ処理
**ファイル**: `src/services/graphrag_sync_service.py` (新規)
- `merge_setting_delta(delta: SettingDelta)` 実装
  - ChromaDB: 該当設定ベクトルの更新 (古いベクトル削除 → 新しいベクトル追加)
  - Knowledge Graph (Neo4j/NetworkX): ノード/エッジの属性更新
  - `delta.merged_to_graphrag = True`, `merged_at = now()` 更新
- バッチ処理対応 (複数 delta をまとめてマージ)

#### Step 16: ネガティブサンプル蓄積・学習データ化
**ファイル**: `src/services/learning_data_service.py` (新規)
- `record_negative_sample(patch_review: PatchReview, resolution: UserResolution)`
  - `rejected` の場合: 「この修正パターンは誤り」としてベクトルDBに保存 (label: negative)
  - `approved` の場合: 正例として保存 (label: positive)
  - `modified` の場合: 差分を正例、元提案を負例として両方保存
- `get_negative_patterns(field_path)` → 類似パターン検索用 API

#### Step 17: AuditAgent に学習データ活用ロジック追加
**ファイル**: `src/agents/audit_agent.py`
- `_load_negative_patterns(field_path)` を監査プロンプトに注入
- 例: 「過去に `magic_system.mana_cost` で『主人公のMP消費が設定より少ない』という指摘がユーザーに却下された → 今回は同パターンを検出しても warning のみに留め、auto-retry しない」
- 信頼度スコアリング調整: ネガティブサンプル数に応じて閾値緩和

#### Step 18: 統合テスト・ドキュメント更新
- **テスト**:
  - `tests/test_patch_review_workflow.py`: レビュー作成→承認→続行、差し戻し→修復、修正案→再レビュー の E2E
  - `tests/test_setting_delta_merge.py`: 手動修正→Delta記録→GraphRAGマージ→検索反映 の E2E
  - `tests/test_negative_learning.py`: 却下パターン→次回監査での挙動変化確認
- **ドキュメント**:
  - `docs/PATCH_REVIEW_WORKFLOW.md`: ユーザー向け操作ガイド
  - `docs/SETTING_VERSIONING.md`: 設定バージョン管理・ロールバック手順
  - `docs/LEARNING_LOOP.md`: ネガティブサンプル蓄積・監査精度向上の仕組み解説

---

## 依存関係グラフ

```
Step 1 ──┬──► Step 5 ──► Step 6 ──► Step 7 ──► Step 10 ──► Step 11 ──► Step 12 ──► Step 13
         │
         ├──► Step 2 ──► Step 14 ──► Step 15
         │                │
         │                └──► Step 16 ──► Step 17
         │
         ├──► Step 3 ──► Step 8 ──► Step 9 ──► Step 10
         │
         └──► Step 4 (マイグレーション: 1-3完了後)
```

---

## 実装優先度・マイルストーン

| マイルストーン | 含むステップ | 目安工数 | 備考 |
|--------------|-------------|---------|------|
| **M1: データ基盤** | 1-4 | 2-3日 | DBスキーマ確定、マイグレーション必須 |
| **M2: バックエンド核心** | 5-9 | 3-4日 | レビューワークフロー完成、API提供 |
| **M3: フロントエンド最小** | 10-13 | 3-4日 | ConflictReportPanel + Sidebar統合 |
| **M4: 学習ループ** | 14-17 | 3-4日 | Delta記録→GraphRAG→負例学習の循環 |
| **M5: 品質保証** | 18 | 1-2日 | テスト・ドキュメント |

**総計: 約 12-17 日 (並列化で短縮可能)**

---

## リスク・注意点

1. **WebSocket vs Polling**: 最初はポーリング実装、後から WebSocket へ切替可能なインターフェース設計
2. **GraphRAG マージの冪等性**: 同一 delta の重複マージ防止 (delta_id で幂等キー管理)
3. **ネガティブサンプルのノイズ**: 却下理由が「方針変更」等の非品質理由の場合除外するフラグ (`is_quality_related`) 必要
4. **バージョン競合**: 複数ユーザー同時編集時の `SettingVersion` 競合解決 (vector clock または last-write-wins + 通知)
5. **パフォーマンス**: diff 生成・GraphRAG マージは非同期ジョブ化推奨 (Huey/Celery)

---

## 今後の拡張余地

- **自動修正提案の精度向上**: 学習データ蓄積後、Fine-tuning / Few-shot プロンプト最適化
- **マルチユーザー協調レビュー**: 複数レビュアーの合議制 (承認には 2名以上同意等)
- **設定変更の影響範囲解析**: 変更フィールドが影響する未執筆エピソードの自動検出・警告
- **ダッシュボード**: 監査精度トレンド、ネガティブサンプル蓄積数、設定変更頻度の可視化