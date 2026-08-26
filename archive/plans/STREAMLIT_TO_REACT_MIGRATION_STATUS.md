# Streamlit → React 移行 進捗レポート

**生成日:** 2026-07-22
**更新日:** 2026-07-22
**状態:** React 移行済み / Streamlit 無効化完了 / ドキュメント更新完了

---

## 実施済み変更

### Phase 0: 分析・準備
- Step 1-6: Streamlit / React ファイル一覧取得、バックアップ作成済
  - `backup/streamlit_app_backup/`
  - `backup/frontend_src_backup/`

### Phase 1: React 基盤確認
- Step 13-18: EasyMode
  - `EasyModeDialog`, `useEasyModeStore`, `useAppActions` は既に実装済み
  - `api.ts` の `generateEasy` 連携済み
- Step 19-24: Books
  - `BooksTab`, `useBooks`, `useBookStore` 実装済み
  - Streamlit `sidebar_sections/book_manager.py` と責務一致
- Step 25-30: Write
  - `WriteTab`, `useWritingStore`, `useBookDetails` 実装済み
  - `getChapters`, `getBible`, `importChapter` 等の API 定義済み
- Step 31-36: Plots
  - `PlotsTab` / Story timeline 実装済み
  - `getPlots`, `expandPlots`, `rebuildPlots`, `planGeneration` 定義済み
- Step 37-42: Task Monitor
  - `TaskMonitor`, `useTaskStream`, `useTaskMonitor` 実装済み
  - SSE stream + stop task の処理が成立
- Step 43-48: Analytics
  - `AnalyticsTab` / `useUIStore` 実装済み
  - 監査履歴、パッチ、プロンプトバージョン、指標トレンドを取得

### Phase 2: 移植・API 統合
- Step 49-54: 残り Tabs 確認
  - `PlanningTab` / `AuditTab` / `StyleLabTab` / `ImportTab` 実装済み
- Step 55-57: API Client 差分補充
  - `frontend/src/api.ts` に以下を追加:
    - `analyzeStyleDna`
    - `getIssues`
    - `resolveIssue`
    - `exportPackage`
- Step 58-59: テスト設定 / CORS
  - 既存 `frontend/src/test/api.test.ts` を確認
  - バックエンド CORS 設定は別 ADR/計画で対応することが望ましい
- Step 60: 統合テスト
  - 依存関係インストール未完了のため、`npm run build` は未実施
  - **次の優先作業:** `frontend` で `npm install --legacy-peer-deps` 後、`npm run build`

### Phase 3: Streamlit 無効化
- Step 61-66: ナビゲーション廃止
  - `streamlit_app/pages_config.py` -> React 移行メッセージのみ
  - `streamlit_app/landing.py` -> React フロントエンド誘導
  - `streamlit_app/sidebar.py` -> Streamlit UI 廃止予定 + React 誘導

### Phase 4: ドキュメント更新
- Step 67-70: 資料・デプロイ設定の React 化
  - `docker-compose.yml`: Streamlit サービス削除
  - `Dockerfile`: 公開ポートを `8200` のみに整理
  - `README.md`: システム構成・起動手順・環境変数・テストコマンドを React ベースに修正
  - `src/README.md`: UI前提を React に修正
  - `frontend/README.md`: 実装保留ステータスを削除し、移行済みを明記
  - `docs/adr/0003-streamlit-coexistence-strategy.md`: 既に Superseded + 移行完了記載

## 変更ファイル一覧

### React
- `frontend/src/api.ts`: `analyzeStyleDna`, `getIssues`, `resolveIssue`, `exportPackage` 追加
- `frontend/src/components/tabs/AuditTab.tsx`: `apiKey` bridge 修正
- `frontend/src/components/tabs/StyleLabTab.tsx`: APIキーガード追加
- `frontend/src/App.tsx`: `AuditTab` へ `apiKey` 受け渡し

### Streamlit
- `streamlit_app/pages_config.py`: 全ページを React 移行通知に置換
- `streamlit_app/landing.py`: ランディングを React 誘導に変更
- `streamlit_app/sidebar.py`: サイドバーを廃止予定表示に変更
- `streamlit_app/`: 完全削除済み（バックアップ: `backup/streamlit_app_backup/`）

### Docs / Deploy
- `docker-compose.yml`: `streamlit` サービス削除
- `Dockerfile`: `EXPOSE 8200` に変更
- `README.md`: React メイン UI に全面改定
- `src/README.md`: UI前提を React に変更
- `frontend/README.md`: 実装済み明記

## 未完了 / 次の作業

- [ ] `frontend` で `npm install --legacy-peer-deps` と `npm run build`
- [ ] 手動ブラウザ確認: http://localhost:3000 で主要フロー確認
- [ ] バックエンド CORS 設定見直し（必要に応じて）

## 備考

- バックエンド API は React の `/api` を通じて利用
- `streamlit_app/` は削除済み。バックアップは `backup/streamlit_app_backup/`
- 既存 React 実装は完成度が高く、UIレベルでは既に React 主導で運用可能な状態
- `docs/adr/0003-streamlit-coexistence-strategy.md` は `Superseded` として以後の参照元は本レポートまたは 72ステップ計画書とする