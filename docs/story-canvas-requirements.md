# ストーリーキャンバス 参考実装要件

作成日: 2026-08-29
参考: OpenWrite (`ilrein/openwrite`), NovelForge (`RhythmicWave/NovelForge`), konva-timeline 等

---

## 1. OpenWrite Story Map (`ilrein/openwrite`) からの要件

### 1.1 概要
- "One sentence becomes a connected story map: a premise node expands into acts, acts into chapters, and a chapter is promoted straight into the manuscript"
- ノードベースの AI 生成: premise → acts → chapters → scenes の階層展開
- Auto-layout 機能つきキャンバス
- Chapter ノードをクリックで原稿（Manuscript）へ昇格

### 1.2 ノード種別
| 種別 | 説明 | autonovel 対応 |
|---|---|---|
| Premise | 作品の核となる一文 | `Book.concept` / `Book.synopsis` から自動生成 |
| Act | 三幕/四幕等の大構造 | 新規ノード種別 `'act'`、`StructureValidator` のテンプレート活用 |
| Chapter | エピソード相当 | 既存 `Plot` (ep_num 1:1) → `'episode'` ノード |
| Scene | チャプター内のシーン | `Plot.scenes` (JSON配列) → `'scene'` ノードとして分割 |

### 1.3 エッジ/関係
- 親子関係: Premise → Act → Chapter → Scene のツリー構造
- 時系列フロー: Chapter 間の順序エッジ
- AI 生成: ノード右クリック/ボタンで「展開」→ 子ノード自動生成

### 1.4 UI/UX
- 無限キャンバス（パン・ズーム）
- ノードドラッグで位置変更（座標保存）
- ノード選択で右側インスペクタ表示
- Auto-layout ボタン（階層整列）

---

## 2. NovelForge (`RhythmicWave/NovelForge`) からの要件

### 2.1 Schema-first カード設計
- `backend/app/schemas/card.py` による型定義
- **カードタイプ** (`CardType`): `json_schema` (JSON Schema) で構造定義
- **カードインスタンス** (`Card`): 任意で `json_schema` 上書き可能
- AI パラメータ: `llm_config_id`, `prompt_name`, `temperature`, `max_tokens` 等をカード単位で設定
- エディタコンポーネント: `editor_component` で描画切替

### 2.2 関係性
- `parent_id` で階層構造
- `display_order` で同階層内順序
- Relation 埋め込み: `$ref` で他タイプの `$defs` を参照可能

### 2.3 ワークフロー (Visual Editor)
- ノードライブラリからドラッグで作成
- 連線で実行順定義
- ノード種別: `Card.Read`, `Card.UpsertChildByTitle`, `Card.ModifyContent`, `List.ForEach`, `List.ForEachRange`
- トリガー: `onsave`, `ongenfinish`, `manual`, `onprojectcreate`

### 2.4 内蔵ワークフローテンプレート
- "プロジェクト作成・雪花創作法"
- "世界観・組織生成"
- "核心蓄圖・落子卡"
- "分卷大綱・落子卡"
- "階段大綱・落章節卡"

**autonovel への適用**: `StoryNode.data` を自由 JSON にし、ノード種別ごとの JSON Schema を将来的に定義可能にする。

---

## 3. konva-timeline / gravity-ui/timeline からの要件

### 3.1 共通機能
- Canvas-based rendering（高性能、大量ノード対応）
- Pan / Zoom / Drag 操作
- タイムライン表示（時間軸またはエピソード軸）
- イベント/バー/マーカー/セクション描画

### 3.2 autonovel では自前実装
- 外部依存を避けるため、HTML `<div>` (ノード) + `<svg>` (エッジ) で実装
- konva 相当のパン/ズームは CSS `transform: translate() scale()` で代用
- タイムライン軸はキャンバス下部に `NarrativeGraph` を埋め込みで代用

---

## 4. autonovel ストーリーキャンバス 要件定義

### 4.1 ノード種別 (`NodeKind`)
```typescript
type NodeKind = 
  | 'premise'      // 作品の核（1作品に1つ）
  | 'act'          // アクト（構造テンプレート由来）
  | 'episode'      // エピソード（Plot 1:1、既存データ）
  | 'scene'        // シーン（Plot.scenes から分割、将来）
  | 'character'    // キャラクター（Character 1:1、既存データ）
  | 'foreshadow'   // 伏線（Foreshadowing 1:1、将来）
```

### 4.2 エッジ種別 (`EdgeKind`)
```typescript
type EdgeKind = 
  | 'flow'         // 時系列の流れ（ep_num 順、episode間）
  | 'part_of'      // 包含関係（act→episode, episode→scene）
  | 'pov'          // 視点キャラ（episode→character）
  | 'dependency'   // 依存（伏線→回収、キャラ成長→発動）
  | 'relationship' // キャラ間関係（character↔character）
```

### 4.3 データモデル (TypeScript)

```typescript
interface StoryNode {
  id: string;              // "node-{uuid}" または "plot-{ep_num}" 等
  book_id: number;
  kind: NodeKind;
  label: string;           // 表示用ラベル
  ep_num?: number;         // episode/scene の場合
  character_id?: number;   // character の場合
  x: number;               // キャンバス座標
  y: number;
  data: Record<string, any>;  // 種別別追加データ（自由 JSON）
  // data 例:
  // episode: { tension, is_catharsis, next_hook, summary, detailed_blueprint }
  // character: { role, traits[], relationships{}, arc_stages[] }
  // act: { structure: 'three_act', beat: 'setup|confrontation|resolution' }
  // premise: { concept, synopsis }
}

interface StoryEdge {
  id: string;              // "edge-{uuid}"
  book_id: number;
  source: string;          // source node id
  target: string;          // target node id
  kind: EdgeKind;
  data?: Record<string, any>;  // 例: { strength: 0.8, label: "伏線" }
}
```

### 4.4 必須機能 (MVP)
1. **キャンバス描画**: ノード絶対配置、エッジ SVG 直線
2. **パン/ズーム**: 右ドラッグパン、ホイールズーム
3. **ノード選択**: クリックで選択、枠線ハイライト
4. **ノードドラッグ**: 位置変更 → 座標保存 API 叩き
4. **インスペクタ**: 右側パネルで label 編集
5. **Seed 自動生成**: 既存 plots → episode ノード、characters → character ノード、構造テンプレート → act ノード
6. **NarrativeGraph 埋め込み**: キャンバス下部にテンション曲線表示
7. **構造警告バッジ**: `/api/structure/validate` 結果を act/episode ノードに表示

### 4.5 将来拡張 (Post-MVP)
- Auto-layout (Dagre 等)
- シーンノード分割 (`Plot.scenes` パース)
- 伏線エッジ (`Foreshadowing` テーブル)
- キャラクター弧火花線 (`CharacterArc.arc_stages`)
- AI によるノード展開 (OpenWrite 風)
- PNG エクスポート

---

## 5. 実装優先順位

| 優先度 | 機能 | ステップ範囲 |
|---|---|---|
| P0 (必須) | バックエンド API + データモデル | 7-18 |
| P0 (必須) | フロント型/ストア/API/タブ統合 | 19-27 |
| P0 (必須) | キャンバス描画・パン/ズーム・ノード表示 | 28-41 |
| P0 (必須) | 選択・インスペクタ・Seed ボタン | 42-45 |
| P1 (重要) | ノードドラッグ・エッジ作成・削除 | 46-57 |
| P1 (重要) | キャラクター弧・テンション曲線・構造警告 | 58-66 |
| P2 (拡張) | PNG エクスポート・ドキュメント・テスト | 67-72 |

---

## 6. 非機能要件

- **依存追加なし**: React Flow, konva, dagre 等は使わない
- **既存ストア準拠**: Zustand パターン踏襲
- **SSOT 準拠**: `api_schemas.py` と `api.ts` で型一致
- **LLM 実装容易性**: 1ステップ=1ファイル編集、複雑ロジックは避ける
- **レスポンシブ**: 幅 100%、高さ `calc(100vh - header)` でフルスクリーン