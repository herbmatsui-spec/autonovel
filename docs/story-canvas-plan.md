# ビジュアルストーリーボード（ストーリーキャンバス）実装計画書

> 対象: autonovel（AI 小説創作エンジン / FastAPI + React+Zustand）
> 目的: 既存の Plot / Chapter / Character データを「視覚的に編集できるキャンバス」として表示し、
>       OpenWrite の Story Map や NovelForge のカード式編集に匹敵する体験を追加する。
> 方針: 低性能 LLM でも 1 ステップずつ確実に実装できるよう、72 の小ステップに分割。

---

## 1. 概要と目標

autonovel は現在、プロットを `PlotsTab` でカード表示、品質を `NarrativeGraph`（Chart.js）で折れ線表示しているが、
「エピソード同士のつながり」「キャラクターの弧」「伏線の回収」を**一つの画面で視覚的に編集**する機能がない。
本計画は新規タブ **🗺️ ストーリーキャンバス** を追加し、以下を実現する。

- エピソード（章）・キャラクター・アクト・シーンを「ノード」としてキャンバスに配置
- ノード間を「エッジ（流れ／依存／関係／伏線）」で結ぶ
- ドラッグ・パン・ズームで自在に配置し、座標を保存
- キャラクター弧をノード脇に火花線で、テンション曲線を下部に埋め込み
- 構造検証（three_act / kishotenketsu / hero_journey）の警告をバッジ表示

参考にした公開リポジトリ:
- **OpenWrite** (`ilrein/openwrite`): premise→acts→chapters→scenes をノード展開する Story Map。
  自前キャンバスで node を auto-layout。本計画の「ノード種別」と「seed 自動生成」の着想元。
- **NovelForge** (`RhythmicWave/NovelForge`): JSON Schema で型付けされたカードと、関係性（relation）編集。
  本計画の `StoryNode.data` を自由 JSON にする柔軟性の着想元。
- **konva-timeline / gravity-ui/timeline**: キャンバス描画の性能手段（本計画では React Flow 風の
  自前 SVG/HTML 実装で代用し、外部依存を最小に留める）。

---

## 2. アーキテクチャ方針（既存コードへの適合）

autonovel の規約に厳密に従う（低性能 LLM が迷わないため）:

- **フロントエンド**
  - データ型は `frontend/src/types/api.ts`（SSOT）に合わせ、`types/storyCanvas.ts` を別途作成して `index.ts` から再エクスポート。
  - 状態は Zustand（`frontend/src/store/`）。既存の `useBookStore` パターンを踏襲した `useStoryCanvasStore` を新規作成。
  - API 呼び出しは `frontend/src/api.ts` の既存関数群（`getPlots` 等）と同じ形式で追加。
  - 通信は `frontend/src/lib/apiClient.ts` の `request<T>`（envelope 自動 unwrap）を再利用。
  - 画面は `frontend/src/components/tabs/` に `StoryCanvasTab.tsx` を追加し、`BookTabBar` の `tabs` 配列へ登録。
  - ルーティングは `router.tsx` の `/book/:id/:step/:tab` を流用（新規 Route は不要）。
  - **描画ライブラリは新規導入せず**、HTML `<div>`（絶対位置）＋ `<svg>`（エッジ）の組み合わせで React Flow 相当を自前実装。
    これは LLM が複雑な外部 API を覚えずに済むため。
- **バックエンド**
  - モデルは `src/backend/database/models.py` の SQLAlchemy に `StoryNode`/`StoryEdge` を追加。
  - スキーマは `src/models/api_schemas.py`（SSOT）に追加。
  - ルーターは `src/backend/routers/` に `story_canvas.py` を新規作成、`server.py` で include。
  - 既存の `/api/structure` 検証と `CharacterArc`/`Foreshadowing` テーブルを再利用。

---

## 3. 実装ステップ（1〜72）

### フェーズ A: 調査と設計（1-6）

1. `frontend/src/types/api.ts` と `src/models/api_schemas.py` で Plot / Chapter / Character / CharacterArc の定義を読み、
   キャンバス化に使えるフィールド（ep_num, title, tension, name, relationships 等）を `docs/story-canvas-notes.md` にメモする。
2. 既存 `PlotsTab.tsx` と `NarrativeGraph.tsx` を読み、キャンバスタブの配置（BookTabBar）と再利用可能部品を `docs/story-canvas-notes.md` に書く。
3. `src/backend/routers/structure.py` の `/api/structure` エンドポイントを読み、キャンバス用エンドポイント命名（`/api/story_canvas`）を決める。
4. OpenWrite / NovelForge の要件を `docs/story-canvas-requirements.md` に箇条書き（ノード種別: premise/act/chapter/scene/character、
   エッジ種別: flow/dependency/relationship/foreshadow）。
5. `frontend/src/types/storyCanvas.ts` の草稿を書く（`StoryNode`, `StoryEdge` の型のみ、まだ本実装しない）。
6. この計画書（ステップ 1-72）を `docs/story-canvas-plan.md` に保存し、マイルストーン（A-G）をチームに共有。

### フェーズ B: バックエンド API（7-18）

7. `src/models/api_schemas.py` に `StoryNodeSchema`（id, book_id, kind, label, ep_num, x, y, data:dict）を追加。
8. 同ファイルに `StoryEdgeSchema`（id, book_id, source, target, kind）を追加。
9. `src/backend/database/models.py` に `StoryNode` / `StoryEdge` の SQLAlchemy モデル（data は JSON/Text 型）を追加。
10. Alembic マイグレーション `alembic/versions/xxxx_story_canvas.py` を生成し、両テーブルを作成。
11. `src/backend/database/repositories/story_canvas_repo.py` を新規作成（get_nodes, get_edges, upsert_node, delete_node, create_edge, delete_edge）。
12. `src/backend/routers/story_canvas.py` を作成し `GET /api/story_canvas/{book_id}`（nodes+edges を返却）を実装。
13. 同ルーターに `PUT /api/story_canvas/{book_id}/nodes`（座標・ラベル保存）を実装。
14. 同ルーターに `POST /api/story_canvas/{book_id}/nodes`（新規ノード作成）を実装。
15. 同ルーターに `DELETE /api/story_canvas/{book_id}/nodes/{node_id}` を実装。
16. 同ルーターに `POST /api/story_canvas/{book_id}/edges` と `DELETE .../edges/{edge_id}` を実装。
17. 既存 plots/characters から初期ノードを生成する `POST /api/story_canvas/{book_id}/seed` を実装（ep_num→chapter ノード、character→character ノード）。
18. `src/backend/server.py` で `story_canvas` ルーターを `include_router`（prefix `/api`）し、起動して `/docs` に出ることを確認。

### フェーズ C: フロントエンド 型・ストア・API（19-27）

19. `frontend/src/types/storyCanvas.ts` を正式定義（`NodeKind = 'episode'|'character'|'act'|'scene'|'premise'` 等）。
20. `frontend/src/types/index.ts` から `storyCanvas` を再エクスポート。
21. `frontend/src/api.ts` に `getStoryCanvas`, `seedStoryCanvas`, `saveStoryNode`, `createStoryNode`, `deleteStoryNode`, `createStoryEdge`, `deleteStoryEdge` を追加（他関数と同じ `request<T>` 形式）。
22. `frontend/src/store/useStoryCanvasStore.ts` を新規作成（state: nodes, edges, selectedId, loading, dirty / actions: setNodes, setEdges, addNode, moveNode, renameNode, removeNode, addEdge, removeEdge, setSelected）。
23. `frontend/src/hooks/useBookDetails.ts` に `getStoryCanvas(bookId)` 呼び出しを追加し、book 読み込み時に store へ投入。
24. `frontend/src/components/BookTabBar.tsx` の `tabs` 配列に `{ id:'story-canvas', label:'ストーリーキャンバス', icon:'🗺️' }` を追加。
25. `frontend/src/components/BookWorkspace.tsx` のタブ switch に `story-canvas` を追加し、lazy import で `StoryCanvasTab` を読み込む。
26. `frontend/src/router.tsx` は既存 `/book/:id/:step/:tab` で済むことを確認（追加 Route 不要、そのまま）。
27. 空実装の `frontend/src/components/tabs/StoryCanvasTab.tsx` を作成（"準備中"のみ表示）し、`npm run build` を通す。

### フェーズ D: キャンバス描画（28-45）

28. `StoryCanvasTab.tsx` に `relative` なコンテナ div を配置し、store の nodes/edges を描画する枠組みを作る。
29. エッジ描画用 `<svg className="absolute inset-0 pointer-events-none">` レイヤーを追加。
30. `drawEdge(a, b)` ユーティリティを作成（単純直線 `M x1 y1 L x2 y2`、のちにベジエ化）。
31. ノード 1 つを描画する `StoryNodeCard.tsx` を作成（絶対位置 div、label 表示のみ）。
32. `StoryNodeCard` に種別ごとの色（episode=blue, character=pink, act=purple, scene=green, premise=amber）を付ける。
33. `StoryNodeCard` に選択枠線スタイルを追加（selectedId と比較して `border-accent`）。
34. store の nodes を `StoryNodeCard` で map 描画し、edges を svg path で描画する。
35. キャンバス背景のグリッド模様を CSS（`background-image: linear-gradient`）で追加。
36. `useStoryCanvasStore` に `pan{x,y}` と `setPan` を追加。
37. キャンバス上の右ドラッグでパンする `onMouseDown/Move/Up` ハンドラを `StoryCanvasTab` に追加。
38. pan オフセットをノードコンテナと svg 両方に `transform: translate()` で適用。
39. ズーム用 `scale` を store に追加し、`onWheel` で ±0.1（0.3〜2.0 クランプ）変更。
40. `transform: translate() scale()` をコンテナと svg に適用。
41. グリッドの背景サイズも `scale` 倍する。
42. ノード選択時に右側 `NodeInspector.tsx` パネルを表示する枠組みを作る。
43. `NodeInspector` に label 編集 input を追加（onChange → `store.renameNode`）。
44. store に `renameNode(id, label)` を追加し、input から呼び出す。
45. `StoryCanvasTab` に「キャンバスを初期化（seed）」ボタンを追加し `seedStoryCanvas` を呼ぶ。

### フェーズ E: インタラクティビティ（46-57）

46. `StoryNodeCard` の `onMouseDown` でドラッグ開始（selectedId 設定＋ドラッグフラグ）。
47. `window` の mousemove でノード位置を更新（移動量を `scale` で割って調整）。
48. mouseup で `saveStoryNode`（座標 PUT）を呼び、store.moveNode を確定。
49. エッジ作成モード: ノードの「＋」ボタンを押すと `linkingFrom` 状態をセット。
50. 別ノード上の mouseup で `createStoryEdge(linkFrom, target)` を呼ぶ。
51. エッジ上に小さな ✕ ボタンを表示し `deleteStoryEdge` を呼ぶ。
52. ノード削除ボタン（🗑）を `StoryNodeCard` に追加し `deleteStoryNode` を呼ぶ。
53. ツールバーに「＋エピソード」「＋キャラクター」ボタン群を追加。
54. ボタンから `createStoryNode(kind)` を呼び、初期座標は画面中央付近に配置。
55. キーボード Delete で選択ノード削除（`StoryCanvasTab` の `onKeyDown`）。
56. 選択ノードをダブルクリックで `PlotsTab` 等へ遷移（ep_num があれば）。
57. dirty フラグをヘッダーに表示し、自動保存（デバウンス 1 秒）を実装。

### フェーズ F: キャラクター弧・タイムライン・構造（58-66）

58. `CharacterArc` テーブルから `getCharacterArcs(bookId)` API を追加（backend + frontend api.ts）。
59. `StoryCanvasTab` 内に「キャラクター弧」オーバーレイトグルを追加。
60. 各 character ノード直下に小さな火花線（SVG polyline）で `arc_stages` を描画。
61. 既存 `NarrativeGraph` の tension 曲線をキャンバス下部パネルに埋め込み（再利用）。
62. `GET /api/structure/books/{id}/validate` の結果をキャンバス上に「構造警告」バッジとして表示。
63. act ノードで episode ノードを囲む半透明の帯（lane）を描画。
64. `Foreshadowing` テーブルから `getForeshadowing` を追加し、伏線を破線エッジとして表示。
65. キャンバス全体の PNG エクスポート（svg→canvas→toDataURL）を実装。
66. エクスポート PNG をダウンロードするリンクを生成。

### フェーズ G: テスト・品質・ドキュメント（67-72）

67. `tests/unit/` に `test_story_canvas_repo.py` を追加（CRUD の最小テスト）。
68. `StoryCanvasTab` のレンダリングを Vitest + Testing Library でスモークテスト。
69. `pre-commit` / `ruff` / `npm run build` / `mypy` を通し、CI が緑になることを確認。
70. `story_canvas` ルーターの OpenAPI 説明（summary/description）を充実。
71. `docs/story-canvas-user-guide.md` を作成（使い方・ノード種別・ショートカット・トラブルシュート）。
72. README の機能一覧に「ストーリーキャンバス」を追加し、PR 用変更サマリを書く。

---

## 4. 低性能 LLM 向けの実装注意

- **1 ステップ = 1 ファイル編集 or 1 関数**に留める。複数ファイルをまたぐステップ（18, 23, 25 など）は
  「既存関数を 1 行追加するだけ」にとどめ、周辺コードを書き換えない。
- **外部ライブラリを導入しない**（React Flow / react-konva 等は使わない）。HTML+SVG 自前実装とし、
  LLM が未知の API を推測する必要をなくす。
- 各ステップの完了時に `npm run build`（frontend）または `ruff`（backend）で**即座に検証**し、
  壊れたらそのステップ内で止める（後戻りしない）。
- 型は `StoryNodeSchema` を SSOT とし、フロント/バックでコピーする際は厳密に一致させる。
- seed（ステップ 17/45）があれば、空の本でも即座にキャンバスが埋まるため、UI 検証が容易。

---

## 5. 期待される効果

- プロット・キャラ・伏線が「一画面」で編集可能になり、NovelForge / OpenWrite 相当の体験を獲得。
- 既存 `NarrativeGraph` や `/api/structure` 検証をキャンバスに統合し、分散していた情報が束ねられる。
- 新規依存ゼロのため、既存 CI / Docker 構成を維持したままマージ可能。
