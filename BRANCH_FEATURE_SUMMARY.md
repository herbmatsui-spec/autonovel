# IFルート分岐・マルチブランチ機能 - 実装完了サマリー

## 概要
このプロジェクトでは、IFルート分岐・マルチブランチ機能のフロントエンド実装を完成させました。バックエンドは既にデータモデル・API・分岐作成/合流ロジックが実装済みであったため、フロントエンドでの分岐可視化・編集UIを重点的に実装しました。

## 実装コンポーネント

### 1. 分岐ツリー可視化コンポーネント (`BranchTree.tsx`)
- React Flowを使用したインタラクティブな分岐ツリー表示
- 自動レイアウトアルゴリズム（簡易的なBFSベース）
- ズーム/パン/ミニマップ機能
- ノード選択・ドラッグ機能
- ブランチ情報（名前、章数、作成日）の表示

### 2. 読者向け分岐選択UI (`BranchSelector.tsx`)
- ドロップダウンによる分岐切替
- URLパラメータとの同期（useSearchParams）
- 現在選択中の分岐のハイライト

### 3. 章レベル差分ビューア (`ChapterDiffViewer.tsx`)
- Unified形式とSide-by-Side形式の差分表示
- モーダルウィンドウでの表示
- ブランチ間の章内容の差分を視覚化

### 4. マージコンフリクトプレビュー・解決システム
#### マージプレビューエンドポイント (`/api/branches/{book_id}/merge/preview`)
- 三方向マージのシミュレーション
- コンフリクト検知（ベース/ソース/ターゲットの変更を比較）
- コンフリクトチャンク単位の詳細表示

#### マージコンフリクトプレビューコンポーネント (`MergeConflictPreview.tsx`)
- 3ペイン表示（Base/Source/Target）
- コンフリクトチャンクごとの解決オプション
  - Baseを採用
  - Sourceを採用  
  - Targetを採用
  - 手動解決
- 解決状況のトラッキング
- すべて解決後のマージ実行ボタン

### 5. 補助的機能・ユーティリティ
#### カスタムフック
- `useBranchTree`: 分岐ツリーデータの取得とキャッシュ
- `useChapterDiff`: 章レベル差分の取得とキャッシュ  
- `useMergePreview`: マージプレビューの取得と mutation

#### ユーティリティ関数 (`src/lib/branches.ts`)
- ブランチツリーのレイアウト算gorith
- ブランチ検索・フィルタリング関数
- 日付フォーマット関数
- ブランチタイプのラベルマッピング

## APIエンドポイント（バックエンド追加分）

### GET `/api/branches/{book_id}/tree`
- 分岐ツリー構造（ノードとエッジ）を取得
- レスポンス形式: `{ nodes: [...], edges: [...] }`

### GET `/api/branches/{book_id}/diff`
- 二つのブランチの指定章の差分を取得
- クエリパラメータ: `branchA`, `branchB`, `chapter`
- レスポンス形式: 章番号、ブランチ名、内容、統一フォーマット差分、サイドバイサイド差分

### POST `/api/branches/{book_id}/merge/preview`
- マージのプレビューとコンフリクト検知
- リクエストボディ: `BranchMergeRequest` (source_branch_id, target_branch_id, merge_ep_num, name?)
- レスポンス形式: マージ可能かどうか、コンフリクトチャンク、マージ後の内容（コンフリクトがない場合）

### POST `/api/branches/{book_id}/merge/commit` (P0 Step 55 実装完了)
- 競合解決済みテキスト群を受け取り、ターゲットブランチの章テーブル (`chapters`) および IF グラフ (`BranchGraph`) をアトミックに確定更新
- EventBus への `branch.merged` イベント発行によるリアルタイム連携
- リクエストボディ: `BranchMergeCommitRequest` (source_branch_id, target_branch_id, merge_ep_num, resolved_chapters, commit_message)
- レスポンス形式: `BranchMergeCommitResponse` (success, target_branch_id, updated_chapters_count, committed_at)

## 依存関係
- frontend:
  - reactflow@11.11.4 (ブランチツリー可視化)
  - @tanstack/react-query@5.102.8 (データ取得とキャッシュ)
- backend:
  - 既存のFastAPI + SQLAlchemy構成を使用
  - 新規依存: なし（標準ライブラリのdifflibのみ使用）

## 使用方法
1. ツリーからブランチを選択（「比較対象として選択」ボタン）
2. もう一方のブランチを選択
3. 章番号を指定して「差分表示」または「マージプレビュー」ボタンをクリック
4. 差分ビューアで章の違いを確認
5. マージプレビューでコンフリクトを解決し、マージ確定コミットを実行

## 実装完了ステータス
✅ P0 マージ確定コミットエンジン統合完了
- バックエンドAPI: `POST /api/branches/{book_id}/merge/commit` を追加
- `BranchMergeService`: アトミックトランザクションによる章コンテンツ更新 & IF グラフ MERGE ノード永続化
- ロールバック保証: 単体テストにて異常時の完全ロールバックを検証済み

## 注意事項
- 差分アルゴリズムは現在簡易的な実装です；より高度な差分表示にはライブラリの使用を検討してください
- マージ確定コミットAPIにより、プレビュー後の確定マージがアトミックに永続化されます
