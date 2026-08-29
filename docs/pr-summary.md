# ストーリーキャンバス実装 PR サマリー

## 変更概要

本PRでは、自動小説創作エンジン「覇権小説エンジン」にストーリーキャンバス機能を実装しました。
これにより、ユーザーは物語の構造を視覚的に編集・分析できるようになります。

## 主な変更点

### バックエンド変更
- **データモデル追加**: `StoryNode` と `StoryEdge` のSQLAlchemyモデルを追加
- **APIスキーマ追加**: `src/models/api_schemas.py` に StoryCanvas 関連スキーマを追加
- **リポジトリ実装**: `src/backend/database/repositories/story_canvas_repo.py` に CRUD 操作を実装
- **APIエンドポイント**: `src/backend/routers/story_canvas.py` に REST API エンドポイントを実装
- **マイグレーション**: Alembic マイグレーションで新しいテーブルを作成
- **ルーター登録**: `src/backend/server.py` に新しいルーターを登録

### フロントエンド変更
- **TypeScript型定義**: `frontend/src/types/storyCanvas.ts` にインターフェースを定義
- **状態管理**: `frontend/src/store/useStoryCanvasStore.ts` に Zustand ストアを実装
- **APIラッパー**: `frontend/src/api.ts` に StoryCanvas 関連 API 関数を追加
- **タイプエクスポート**: `frontend/src/types/index.ts` にエクスポートを追加
- **タブ統合**: 
  - `frontend/src/components/BookTabBar.tsx` にタブを追加
  - `frontend/src/components/BookWorkspace.tsx` に lazy import とスイッチケースを追加
- **キャンバスコンポーネント**: `frontend/src/components/tabs/StoryCanvasTab.tsx` を実装
  - ノード・エッジの描画（SVG + HTML）
  - ドラッグ・パン・ズーム機能
  - ノード選択とインスペクターパネル
  - エッジ作成・削除機能
  - ノード作成・削除機能
  - リンクモード（Lキー）
  - キャラクター弧スパークライン表示
  - ナラティブタイムライン表示（エキスパートモード）
  - ツールバーによるノード作成
  - キーボードショートカットサポート
  - 自動保存デバウンス機能

## ファイル変更リスト

### 新規追加ファイル
- `src/backend/database/repositories/story_canvas_repo.py`
- `src/backend/routers/story_canvas.py`
- `src/backend/alembic/versions/115dcdfc0063_add_story_canvas_tables_story_nodes_.py`
- `frontend/src/types/storyCanvas.ts`
- `frontend/src/store/useStoryCanvasStore.ts`
- `frontend/src/components/tabs/StoryCanvasTab.tsx`
- `frontend/src/components/tabs/__tests__/StoryCanvasTab.test.tsx`
- `tests/unit/test_story_canvas_repo.py`
- `docs/story-canvas-notes.md`
- `docs/story-canvas-requirements.md`
- `docs/story-canvas-plan.md` (このファイル)
- `docs/story-canvas-user-guide.md`

### 変更ファイル
- `src/models/api_schemas.py`
- `src/backend/database/models.py`
- `src/backend/server.py`
- `frontend/src/types/index.ts`
- `frontend/src/hooks/useBookDetails.ts`
- `frontend/src/components/BookTabBar.tsx`
- `frontend/src/components/BookWorkspace.tsx`
- `frontend/src/components/tabs/StoryCanvasTab.tsx` (新規作成後に大幅更新)
- `README.md`

## テスト状況

- バックエンドリポジトリのユニットテストを実装済み
- フロントエンドコンポーネントの基本テストを実装済み
- ビルド・lintチェック済み（既存のlint警告は変更前から存在）

## 実装状況

✅ フェーズA: 調査と設計 (1-6) - 完了
✅ フェーズB: バックエンド API (7-18) - 完了
✅ フェーズC: フロントエンド型・ストア・API (19-27) - 完了
✅ フェーズD: キャンバス描画 (28-45) - 完了
✅ フェーズE: インタラクティビティ (46-57) - 完了
✅ フェーズF: キャラクター弧・タイムライン・構造 (58-66) - 完了
✅ フェーズG: テスト・品質・ドキュメント (67-72) - 完了

## 使用方法

1. 作品を選択してブックワークスペースを開く
2. ツールバーの「ストーリーキャンバス」タブをクリック
3. 「🌱 キャンバスを初期化 (Seed)」ボタンをクリックして初期データを生成
4. ノードをドラッグして配置を調整
5. ノードの「+」ボタンまたはLキーでリンクモードを開始し、エッジを作成
6. 右側インスペクターパネルでノード詳細を編集
7. Deleteキーでノード削除、エッジ上の×ボタンでエッジ削除
8. エキスパートモードではキャラクター弧とナラティブタイムラインが表示

## 今後の課題

- [ ] シーンノードのサポート
- [ ] 伏線エッジの自動生成
- [ ] 自動レイアウト機能
- [ ] PNG/SVG エクスポート機能
- [ ] コメント・注釈機能