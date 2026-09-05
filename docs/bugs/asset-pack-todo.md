# AssetPackPanel 機能 TODO (Step 33 調査結果)

## 現状 (2026-09-05)

### フロントエンド
- `frontend/src/components/AssetPackPanel.tsx` で IF / Media-Mix / eBook を ZIP 一括生成する UI 実装済み
- `useMultimedia` hook 経由で `/multimedia/...` を呼び出し
- Phase 8 修正 (Step 31-32) で **ヘッダ「🖼️ 画像生成」ボタン** + モーダル表示を追加済み
- Studio モードではタブバーから「🖼️ マルチメディア」タブでも到達可能 (Step 4-6)

### バックエンド
- `src/backend/routers/multimedia.py` に 7 個のエンドポイント実装済み
- `src/services/illustration/` でイラスト生成パイプライン稼働

## 残 TODO (バックエンド完全疎通確認)

### 必須: 結合テスト
- [ ] `/multimedia/generate` 起動 → task_id 取得
- [ ] `/multimedia/tasks/{task_id}` ポーリングで `completed` 到達
- [ ] `/multimedia/files/{filename}` から ZIP ダウンロード
- [ ] ZIP 内に IF / Media-Mix / eBook が含まれる

### 任意: UI 改善
- [ ] 各フォーマット (epub/pdf/mobi/manga/...) ごとの進捗バー
- [ ] 失敗時のリトライ UX
- [ ] 多言語対応 (現状英語のみ)

### 関連ファイル
- `frontend/src/components/AssetPackPanel.tsx`
- `frontend/src/hooks/useMultimedia.ts`
- `src/backend/routers/multimedia.py`
- `src/services/illustration/`
- `src/infrastructure/database/models/multimedia_*.py`

## 既知の制限
- `bookId` が 0 や未指定だと 422 エラー (`Path(ge=1)` 制約)
- `multimedia/generate` は非同期タスクのためポーリング必須 (現状 10s 間隔)
- 生成には LLM API キー必須 (`.env` で設定)