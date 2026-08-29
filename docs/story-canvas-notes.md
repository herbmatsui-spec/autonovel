# ストーリーキャンバス実装のためのデータモデル調査メモ

作成日: 2026-08-29
参考: `frontend/src/types/api.ts`, `src/models/api_schemas.py`, `src/backend/database/models.py`, `src/domain/models/`

---

## 1. 既存モデルから抽出可能なフィールド

### 1.1 Plot / Episode (プロット・エピソード)
| 要素 | フロント型 (`api.ts`) | バックエンド SSOT (`api_schemas.py`) | DB (`models.py`) | ドメイン (`PlotDbModel`) |
|---|---|---|---|---|
| エピソード番号 | `ep_num: number` | `ep_num: int` | `ep_num` | `ep_num: int` |
| タイトル | `title: string` | `title: str` | `title` | `title: Optional[str]` |
| 概要 | `summary: string` | `summary: str` | `summary` | `summary: Optional[str]` |
| 詳細設計図 | `detailed_blueprint?: string` | `detailed_blueprint: Optional[str]` | `detailed_blueprint` | `detailed_blueprint: Optional[str]` |
| テンション | `tension?: number` | `tension: float = 50.0` | `tension` (int) | `tension: Optional[int]` |
| カタルシス有無 | `is_catharsis?: boolean` | `is_catharsis: bool = False` | `is_catharsis` | `is_catharsis: Optional[bool]` |
| ステータス | `status?: string` | `status: str = "open"` | `status` | `status: Optional[str]` |
| 次のフック | `next_hook?: string` | (SSOTに未定義) | `next_hook` (JSON) | `next_hook: Optional[Dict]` |
| シーン配列 | (なし) | (なし) | `scenes` (JSON) | `scenes: Optional[List[Dict]]` |
| 恋愛メーター | (なし) | (なし) | `love_meter` | `love_meter: Optional[int]` |
| catharsis_type | (なし) | (なし) | `catharsis_type` | `catharsis_type: Optional[str]` |
| POV キャラ | (なし) | (なし) | `pov_character_id` | (なし) |
| スクリプト内容 | `plot_variants?` / `script_content` | `script_content: Optional[str]` | `script_content` | `script_content: Optional[str]` |

**キャンバス活用ポイント**:
- `ep_num` → ノードの順序・識別子
- `title` + `summary` → ノードのラベル表示
- `tension` → ノードの色・サイズ・バッジ
- `is_catharsis` / `catharsis_type` → 特殊バッジ
- `scenes` → ノード内部の展開可能な子アイテム（シーンノードとして分割可能）
- `next_hook` → 次エピソードへのエッジ情報

---

### 1.2 Chapter (本文・章)
| 要素 | フロント型 | DB |
|---|---|---|
| エピソード番号 | `ep_num: number` | `ep_num` |
| タイトル | `title: string` | `title` |
| 本文 | `content: string` | `content` |
| 概要 | `summary: string` | `summary` |
| 品質スコア | `quality_score?` | `score_story` |
| キラーフレーズ | `killer_phrase?` | `killer_phrase` |

**活用**: Plot ノードと 1:1 対応。Plot ノードの詳細パネルで表示。

---

### 1.3 Character (キャラクター) - DBのみ、フロント未公開
| 要素 | DB (`models.py`) | ドメイン (`CharacterDbModel`) |
|---|---|---|
| ID | `id` | `id` |
| 作品ID | `book_id` | `book_id` |
| 名前 | `name` | `name` |
| 役割 | `role` | `role` |
| 詳細データ(JSON) | `registry_data` (Text) | `registry_data: Optional[Union[dict, str]]` |

`registry_data` に含まれる想定フィールド（ドメイン層 `Character` で定義）:
- `traits: List[str]`
- `background: str`
- `relationships: Dict[str, str]`
- `current_emotion: str`
- `tension_contribution: float`
- `emotional_resonance: float`

**活用**: キャラクターノードとして配置。`registry_data` から感情弧・関係性を抽出。

---

### 1.4 CharacterArc (キャラクター弧)
| 要素 | DB (`models.py`) |
|---|---|
| ID | `id` |
| 作品ID | `book_id` |
| キャラID | `character_id` (FK) |
| 弧名 | `arc_name` |
| 段階配列(JSON) | `arc_stages` (Text, default `"[]"`) |
| 現在段階インデックス | `current_stage_index` |
| 完了フラグ | `is_completed` |

**活用**: キャラクターノード直下に「火花線グラフ」として `arc_stages` を可視化。

---

### 1.5 Foreshadowing (伏線)
| 要素 | DB (`models.py`) |
|---|---|
| ID | `id` |
| 作品/ブランチ/話数 | `book_id`, `branch_id`, `ep_num` |
| 種類 | `type` (例: "item", "secret", "promise") |
| 説明 | `description` |
| 場所 | `location` |
| 回収話数 | `payoff_ep` (nullable) |
| 回収場所 | `payoff_location` |
| 強度 | `strength` (float) |
| 達成フラグ | `fulfilled` (bool) |

**活用**: 破線エッジで `ep_num` → `payoff_ep` を結ぶ。「伏線」トグルで表示/非表示。

---

### 1.6 NarrativeMetric (テンション曲線等)
| 要素 | DB (`models.py`) |
|---|---|
| 作品/章 | `book_id`, `chapter_id` |
| 指標名 | `metric_name` (例: "tension", "emotional_satisfaction", "mystery_density") |
| 値 | `metric_value` |
| 記録時刻 | `recorded_at` |

**活用**: 既存 `NarrativeGraph` と同データ。キャンバス下部に埋め込み再利用。

---

### 1.7 Structure Validation (構造検証)
既存エンドポイント: `GET /api/structure/books/{id}/validate?structure=three_act|kishotenketsu|hero_journey`
（`src/backend/routers/structure.py` → `src/services/structure_validator.py`）

返却: `missing_beats`, `climax_position`, `pacing_issues` 等。
**活用**: キャンバス上部に「構造警告」バッジとして表示。

---

## 2. キャンバス用ノード種別 設計案

```typescript
type NodeKind = 
  | 'premise'      // 作品の核（1つ）
  | 'act'          // アクト（三幕構成等）
  | 'episode'      // エピソード（Plot 1:1）
  | 'scene'        // シーン（Plot.scenes から分割）
  | 'character'    // キャラクター
  | 'foreshadow'   // 伏線（独立ノード or エッジ扱い）
```

---

## 3. キャンバス用エッジ種別 設計案

```typescript
type EdgeKind = 
  | 'flow'         // 時系列の流れ（ep_num 順）
  | 'dependency'   // 依存（伏線→回収、キャラ成長→発動）
  | 'relationship' // キャラ間関係
  | 'part_of'      // act に含まれる episode, episode に含まれる scene
  | 'pov'          // episode の視点キャラ
```

---

## 4. 既存 UI 再利用可能部品

| 部品 | ファイル | 再利用方法 |
|---|---|---|
| `NarrativeGraph` | `frontend/src/components/NarrativeGraph.tsx` | キャンバス下部パネルにそのまま埋め込み（props で data 渡し） |
| `PlotsTab` カード表示 | `frontend/src/components/tabs/PlotsTab.tsx` | ノードカードのベース UI |
| `BookTabBar` | `frontend/src/components/BookTabBar.tsx` | `tabs` 配列に `story-canvas` 追加 |
| `BookWorkspace` | `frontend/src/components/BookWorkspace.tsx` | タブ switch に `story-canvas` 追加 |
| `router.tsx` | `frontend/src/router.tsx` | 既存 `/book/:id/:step/:tab` 利用（新規 Route 不要） |

---

## 5. API エンドポイント命名規則

既存: `/api/plots/{book_id}`, `/api/chapters/{book_id}`, `/api/bibles/{book_id}`, `/api/narrative_metrics/{book_id}/{branch_id}`, `/api/structure/books/{id}/validate`

新規: `/api/story_canvas/{book_id}` (GET nodes+edges, PUT nodes, POST nodes, DELETE nodes, POST edges, DELETE edges, POST seed)

---

## 6. ステップ 2 結果: PlotsTab / NarrativeGraph / BookWorkspace 調査

### 6.1 PlotsTab.tsx (113 行)
- `useBookStore()` から `selectedBook`, `plots` を取得
- `plots` は `Plot[]` 配列（`ep_num, title, summary, detailed_blueprint, tension, is_catharsis, status, next_hook, plot_variants`）
- 表示: エピソードごとにカード (`border rounded-lg p-4 bg-card shadow-sm`)
- ヘッダー: 「エピソード {ep_num}: {title}」＋ `next_hook` バッジ（rose色）
- 本文: `summary` (prose)、`detailed_blueprint` (暗背景小文字)
- 右上: 詳細ボタン（未実装プレースホルダ）
- 上部: 複数案切り替えバー（案 A/B/C、UIのみ、データ未連携）
- アクション: `handleExpandPlots`（自動生成）

**再利用可能部品**: カードレイアウト、プロット配列の map 表示、バッジ表示、次へのフック表示

### 6.2 NarrativeGraph.tsx (229 行)
- Props: `data: NarrativeMetricTrend[]`, `onSceneClick(epNum, sceneNum)`
- 内部状態: `selectedMetrics` (デフォルト 3指標), `periodFilter` (開始/終了話数)
- Chart.js (`react-chartjs-2`) で折れ線グラフ描画
- 実線: 実測値、`d.scores[metric]` から抽出
- 破線: 理想カーブ（テンション=sin波、感情充足=直線増加、謎密度=定数）
- X軸: `Ep{ep_num}-S{scene_num}` ラベル
- ツールバー: 指標トグルボタン、期間フィルタ select
- クリック時: `onSceneClick` コールバック（親で toast 表示等）
- 空データ時: プレースホルダ表示

**再利用方法**: `AnalyticsTab` と同様に `StoryCanvasTab` 内で `<NarrativeGraph data={metricTrend} onSceneClick={...} />` として埋め込み可能。

### 6.3 AnalyticsTab.tsx (133 行) での使用例
- `useUIStore()` から `metricTrend` 取得
- `isExpertMode` (userSettingsStore) 時のみ表示
- `<NarrativeGraph data={metricTrend} onSceneClick={...} />`

### 6.4 BookWorkspace.tsx (172 行) - タブ統合の実態
- `useParams` で `id`, `step`, `tab` を取得
- タブ時 (`tabParam` あり): `BookTabBar` + `StepShell` + `TabComponent` (lazy import)
- ステップ時 (`tabParam` なし): `StepComponent` (switch 文)
- `TabComponent` switch: `style-lab` | `plots` | `analytics` → ここに `story-canvas` 追加
- `BookTabBar` の `tabs` 配列にタブ定義 → ここに追加
- `router.tsx`: `/book/:id/:step/:tab` 既存、新規 Route 不要

**統合手順確定**:
1. `BookTabBar.tsx` の `tabs` 配列に追加
2. `BookWorkspace.tsx` の lazy import + `TabComponent` switch に追加
3. `router.tsx` 変更不要

---

## 7. ステップ 3 結果: Structure Router 調査

### 7.1 既存エンドポイント
- `GET /api/structure/templates` → 利用可能テンプレート一覧
- `GET /api/structure/books/{book_id}/validate?structure=three_act|kishotenketsu|hero_journey`
  - 返却: `validate(plots, structure)` の結果（`missing_beats`, `climax_position`, `pacing_issues` 等）

### 7.2 キャンバス用エンドポイント命名確定
- ベース: `/api/story_canvas/{book_id}`
- エンドポイント一覧:
  - `GET    /api/story_canvas/{book_id}`           → nodes + edges 取得
  - `PUT    /api/story_canvas/{book_id}/nodes`     → 座標・ラベル一括保存
  - `POST   /api/story_canvas/{book_id}/nodes`     → 新規ノード作成
  - `DELETE /api/story_canvas/{book_id}/nodes/{node_id}` → ノード削除
  - `POST   /api/story_canvas/{book_id}/edges`     → エッジ作成
  - `DELETE /api/story_canvas/{book_id}/edges/{edge_id}` → エッジ削除
  - `POST   /api/story_canvas/{book_id}/seed`      → 既存 plots/characters から初期生成

### 7.3 次ステップ
**ステップ 4**: 参考実装要件を `docs/story-canvas-requirements.md` にまとめる。
**ステップ 5**: `frontend/src/types/storyCanvas.ts` の草稿を書く。
**ステップ 6**: この計画書を `docs/story-canvas-plan.md` に保存（既に完了）。