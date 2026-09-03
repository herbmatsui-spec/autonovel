# ドキュメント修正実装計画書

**作成日:** 2026-09-03
**ステータス:** 📋 レビュー待ち
**優先度:** P2 (ドキュメント陳腐化) / P3 (内部設計参照ズレ)

---

## 概要

本計画書は、README.md のドキュメントと実装체의 불일치를修正するための詳細な実装手順を定義する。

| 項目 | 優先度 | 修正コスト | 影響範囲 |
|------|--------|------------|----------|
| フロントエンドディレクトリ階層修正 | P2 | 小 | §2.3, §3.3 |
| EventBus 二重実装の文書化 | P2 | 中 | §4.1 |
| 未記載路由器の追加 | P2 | 小 | §3.4, §8.1 |
| EpisodePipeline 位置的修正 | P3 | 小 | §4.1, §8.1 |
| Workflows 層の文書化 | P3 | 中〜大 | §4, §8.1 |

---

## 1. フロントエンドディレクトリ階層修正 (P2)

### 1.1 現状問題

README §2.3 および §3.3 で `StudioWorkspace.tsx` が `editor/` 配下に記載されているが、
実際は `studio/` 配下に配置されている。

```
【実際】frontend/src/components/studio/StudioWorkspace.tsx
【README】frontend/src/components/editor/StudioWorkspace.tsx (誤記)
```

また、`AssetPackPanel.tsx` が存在しますが、README に一切記載がありません。

### 1.2 修正対象ファイル

- `README.md` §2.3 (line 231-250)
- `README.md` §3.3 (line 434-445)

### 1.3 修正内容

#### §2.3 修正 (StudioWorkspace.tsx のパス修正)

**現在:**
```
- **`src/components/editor/StudioWorkspace.tsx`**: 3カラム統合ワークスペース
```

**修正後:**
```
- **`src/components/studio/StudioWorkspace.tsx`**: 3カラム統合ワークスペース
- **`src/components/AssetPackPanel.tsx`**: アセットパック生成・進捗管理パネル
```

#### §3.3 修正

**現在 (line 442):**
```
- **`src/components/editor/Editor.tsx`**: 本文編集用リッチエディタ
```

**修正後:**
```
- **`src/components/studio/`**: 上級者Studioコンポーネント群
  - `StudioWorkspace.tsx`: 3カラム統合ワークスペース
  - `ChapterOutlineTree.tsx`: 章構成ツリービュー
- **`src/components/editor/`**: エディタ機能コンポーネント群
  - `Editor.tsx`: 本文編集用リッチエディタ
  - `InlineAiToolbar.tsx`: インライン五感推敲ツールバー
  - `NextBeatsPanel.tsx`: 次の展開3案生成パネル
  - `EditorialSidebar.tsx`: 専属AI編集者(Q&A/矛盾診断)
  - `AiSuggestions.tsx`: AI提案ポップオーバー
  - `ConflictModal.tsx`: 設定矛盾モーダル
- **`src/components/AssetPackPanel.tsx`**: マルチメディアアセットパック進捗管理
```

---

## 2. EventBus 二重実装の文書化 (P2)

### 2.1 現状問題

README §4.1 では `src/agents/event_bus.py` の EventBus のみを言及しているが、
実際には以下の2つの類似ファイルが存在する:

| ファイル | 用途 | 規模 |
|----------|------|------|
| `src/agents/event_bus.py` | エージェント間オーケストレーションイベント | 28行 |
| `src/shared/event_bus.py` | Streamlit UI イベント型 ( kernels/ → streamlit_app/ のbridge) | 23行 |

### 2.2 修正対象ファイル

- `README.md` §4.1 (line 493-532)

### 2.3 修正内容

**現在 (line 496):**
```
エージェント間のルーティングは `src/agents/orchestrator.py` の `AgentName` / `AgentContext` / `AgentResult` ベースのグラフで表現され、
各エージェントの実行は `src/agents/event_bus.py` の `EventBus`（in-process + Redis Pub/Sub）で観測できます。
```

**修正後:**
```
エージェント間のルーティングは `src/agents/orchestrator.py` の `AgentName` / `AgentContext` / `AgentResult` ベースのグラフで表現される。

 EventBus は2種類存在する:
 - **`src/agents/event_bus.py` EventBus**: エージェント間オーケストレーションイベント用 (in-process + Redis Pub/Sub)
 - **`src/shared/event_bus.py` UIEventType**: Streamlit UI 向けイベント種別定義 (kernels/ → streamlit_app/ 間のbridge)
```

---

## 3. 未記載路由器の追加 (P2)

### 3.1 現状問題

README §3.4 および §8.1 の路由器一覧・構成図から以下のファイルが欠落している:

**欠落路由器一覧 (16個 + α):**

| 路由器ファイル | エンドポイント | ステータス |
|---------------|----------------|------------|
| `cost.py` | `/cost/*` | 完全欠落 |
| `hooks.py` | `/hooks/*` | 完全欠落 |
| `issues.py` | `/issues/*` | 完全欠落 |
| `structure.py` | `/structure/*` | 完全欠落 |
| `commercial.py` | `/commercial/*` | 完全欠落 |
| `patches.py` | `/patches/*` | 完全欠落 |
| `tasks.py` | `/tasks/*` | 完全欠落 |
| `misc.py` | `/misc/*` | 完全欠落 |
| `novel.py` | `/novel/*` | 完全欠落 |
| `orchestrated.py` | `/orchestrated/*` | 完全欠落 |
| `trace.py` | `/trace/*` | 完全欠落 |
| `export.py` | `/export/*` | 一部記載 (§2.7, §13) |
| `collab.py` | `/collab/*` | 一部記載 (§2.7.2, §13) |
| `styles.py` | `/styles/*` | 一部言及 (server.py line 48) |
| `editor.py` | `/editor/*` | 一部言及 (server.py line 50) |
| `promp_compare.py` | `/prompt_compare/*` | 一部記載 (§3.4) |
| `health.py` | `/health/*` | §16 で言及 |

### 3.2 修正対象ファイル

- `README.md` §3.4 (line 448-464)
- `README.md` §8.1 ディレクトリツリー (line 877-1020)

### 3.3 修正内容

#### §3.4 修正 (路由器一覧の拡充)

**現在:**
```markdown
- **`routers/easy_mode.py`**: かんたんモードの全エンドポイント（執筆、ポーリング、ZIP納品、ガチャ、ダイジェスト、昇格、IF分岐昇格）。
- **`routers/books.py`, `plots.py`, `episodes.py`**: 作品・章・プロットのCRUDおよびブランチ操作。
- **`routers/graph.py`**: ナレッジグラフのノード・エッジデータ取得およびエンティティ検索。
- **`routers/illustrations.py`**: 挿絵プロンプト生成および画像生成ジョブ管理。
- **`routers/marketing.py`**: マーケティング資料・あらすじ・キャッチコピー生成。
- **`routers/multimedia.py`** (`ENABLE_MULTIMEDIA`): シーン画像 / 立ち絵 / 表紙 / ボイス / BGM のアセットパック管理。
- **`routers/collab.py`**: コメントツリーと `ChapterVersion` (CRDT ベクタークロック) による共同編集 API。
- **`routers/prompt_versions.py`, `prompt_compare.py`**: プロンプトのバージョン管理・A/B 比較。
- **`routers/streaming.py`**: SSE による長文生成のリアルタイム配信。
- **`routers/export.py`**: eBook (EPUB) エクスポート・詳細エクスポート。
- **`observability.py`**: `/health`（多段ヘルスチェック）および `/metrics`（プロセス内メトリクス）。
- **`rate_limit.py`**: IP単位スライディングウィンドウ方式による過剰リクエスト制限 (HTTP 429)。
```

**修正後:**
```markdown
- **`routers/easy_mode.py`**: かんたんモードの全エンドポイント（執筆、ポーリング、ZIP納品、ガチャ、ダイジェスト、昇格、IF分岐昇格）。
- **`routers/books.py`, `plots.py`, `episodes.py`**: 作品・章・プロットのCRUDおよびブランチ操作。
- **`routers/graph.py`**: ナレッジグラフのノード・エッジデータ取得およびエンティティ検索。
- **`routers/illustrations.py`**: 挿絵プロンプト生成および画像生成ジョブ管理。
- **`routers/marketing.py`**: マーケティング資料・あらすじ・キャッチコピー生成。
- **`routers/multimedia.py`** (`ENABLE_MULTIMEDIA`): シーン画像 / 立ち絵 / 表紙 / ボイス / BGM のアセットパック管理。
- **`routers/collab.py`**: コメントツリーと `ChapterVersion` (CRDT ベクタークロック) による共同編集 API。
- **`routers/prompt_versions.py`, `prompt_compare.py`**: プロンプトのバージョン管理・A/B 比較。
- **`routers/streaming.py`**: SSE による長文生成のリアルタイム配信。
- **`routers/export.py`**: eBook (EPUB) エクスポート・詳細エクスポート。
- **`routers/cost.py`**: コスト分析・トークン使用量追踪 API。
- **`routers/hooks.py`**: フック(イベントトリガー)管理 API。
- **`routers/issues.py`**: 品質監査で検知された問題(Issue)管理 API。
- **`routers/structure.py`**: 作品構造(章構成・プロットツリー)管理 API。
- **`routers/commercial.py`**: 商用展開・収益化設定管理 API。
- **`routers/patches.py`**: 自動修正パッチ(Patch)管理 API。
- **`routers/tasks.py`**: タスク状態管理・一覧取得 API。
- **`routers/misc.py`**: 雑多なユーティリティエンドポイント群。
- **`routers/novel.py`**: 小说詳細・メタデータ管理 API。
- **`routers/orchestrated.py`**: オーケストレーション統合 API。
- **`routers/trace.py`**: 実行トレース・ログ取得 API。
- **`routers/editor.py`**: 上級者Studioエディタ状態管理 API。
- **`routers/styles.py`**: 文体プリセット・スタイル管理 API。
- **`observability.py`**: `/health`（多段ヘルスチェック）および `/metrics`（プロセス内メトリクス）。
- **`rate_limit.py`**: IP単位スライディングウィンドウ方式による過剰リクエスト制限 (HTTP 429)。
```

#### §8.1 ディレクトリツリー修正

**現在 (line 897):**
```text
│   │   ├── routers/                   # API ルーター群 (~30)
│   │   │   ├── easy_mode.py           # かんたんモード API (生成/ポーリング/ZIP納品/ガチャ/昇格)
│   │   │   ├── books.py, plots.py, episodes.py
│   │   │   ├── graph.py               # ナレッジグラフデータ提供 API
│   │   │   ├── illustrations.py, marketing.py
│   │   │   ├── multimedia.py          # マルチメディアアセットパック API (ENABLE_MULTIMEDIA)
│   │   │   ├── collab.py              # 共同編集 (ChapterVersion / Comments)
│   │   │   ├── prompt_versions.py, prompt_compare.py
│   │   │   ├── export.py              # eBook (EPUB) エクスポート
│   │   │   ├── streaming.py           # SSE リアルタイムストリーミング
│   │   │   └── ...                    # novel, hooks, structure, patches, styles, etc.
```

**修正後:**
```text
│   │   ├── routers/                   # API ルーター群 (31)
│   │   │   ├── easy_mode.py           # かんたんモード API (生成/ポーリング/ZIP納品/ガチャ/昇格)
│   │   │   ├── books.py               # 作品 CRUD
│   │   │   ├── plots.py               # プロット CRUD
│   │   │   ├── episodes.py            # エピソード CRUD
│   │   │   ├── graph.py               # ナレッジグラフデータ提供 API
│   │   │   ├── illustrations.py       # 挿絵プロンプト生成
│   │   │   ├── marketing.py           # マーケティング資料生成
│   │   │   ├── multimedia.py          # マルチメディアアセットパック API (ENABLE_MULTIMEDIA)
│   │   │   ├── collab.py              # 共同編集 (ChapterVersion / Comments)
│   │   │   ├── prompt_versions.py     # プロンプトバージョン管理
│   │   │   ├── prompt_compare.py      # プロンプト A/B 比較
│   │   │   ├── export.py              # eBook (EPUB) エクスポート
│   │   │   ├── streaming.py           # SSE リアルタイムストリーミング
│   │   │   ├── cost.py                # コスト分析・トークン追跡
│   │   │   ├── hooks.py               # イベントフック管理
│   │   │   ├── issues.py              # 品質Issue管理
│   │   │   ├── structure.py           # 作品構造管理
│   │   │   ├── commercial.py          # 商用展開設定
│   │   │   ├── patches.py            # 自動修正パッチ管理
│   │   │   ├── tasks.py              # タスク状態管理
│   │   │   ├── misc.py               # ユーティリティ群
│   │   │   ├── novel.py              # 小説詳細・メタデータ
│   │   │   ├── orchestrated.py       # オーケストレーション統合
│   │   │   ├── trace.py              # 実行トレース取得
│   │   │   ├── editor.py             # Studioエディタ状態管理
│   │   │   ├── styles.py             # 文体プリセット管理
│   │   │   ├── health.py             # ヘルスチェック (冗長、observability.pyを使用)
│   │   │   └── __init__.py
```

---

## 4. EpisodePipeline 位置的修正 (P3)

### 4.1 現状問題

README §4.1 および §8.1 で EpisodePipeline の位置が誤って記載されている:

| 項目 | README 記載 | 実際 |
|------|-------------|------|
| EpisodePipeline | `src/agents/writing/` 配下 | `src/agents/episode_pipeline.py` (独立ファイル) |

### 4.2 修正対象ファイル

- `README.md` §4.1 (line 532)
- `README.md` §8.1 (line 922)

### 4.3 修正内容

#### §4.1 修正 (line 532)

**現在:**
```
> **StreamPlotScheduler (`src/agents/writing_scheduler.py`) + `EpisodePipeline`**: 章単位の生成をストリーム配信・チェックポイント保存で進行させ、長文でも停止・再開可能。
```

**修正後:**
```
> **StreamPlotScheduler (`src/agents/writing_scheduler.py`) + `EpisodePipeline` (`src/agents/episode_pipeline.py`)**: 章単位の生成をストリーム配信・チェックポイント保存で進行させ、長文でも停止・再開可能。
```

#### §8.1 ディレクトリツリー修正 (line 922)

**現在:**
```text
│   │   ├── agents/                        # マルチエージェント知能層
...
│   │   │   ├── writing/                   # WritingAgent + episode_writer, bible_extractor, rewrite_orchestrator
```

**修正後:**
```text
│   │   ├── agents/                        # マルチエージェント知能層
...
│   │   │   ├── writing/                   # WritingAgent + episode_writer, bible_extractor, rewrite_orchestrator
│   │   │   ├── episode_pipeline.py       # エピソード執筆パイプライン (ストリーム配信/チェックポイント)
```

---

## 5. Workflows 層の文書化 (P3)

### 5.1 現状問題

README §4 および §8.1 で、`src/backend/workflows/` 配下の19種類のワークフローが
一切記載されていない。マルチエージェント協調の設計図が大幅に古い。

**存在しないワークフロー:**

| ワークフロー | 用途 |
|--------------|------|
| `base_workflow.py` | ワークフロー基底クラス |
| `easy_mode_workflow.py` | かんたんモード統合ワークフロー |
| `episode_writing_workflow.py` | エピソード執筆ワークフロー |
| `full_auto_workflow.py` | 完全自動執筆ワークフロー |
| `plot_expansion_workflow.py` | プロット展開ワークフロー |
| `plot_rebuild_workflow.py` | プロットリビルドワークフロー |
| `reverse_plot_workflow.py` | 逆算プロットワークフロー |
| `critique_optimization_workflow.py` | 批評最適化ワークフロー |
| `illustration_workflow.py` | 挿絵生成ワークフロー |
| `marketing_generation_workflow.py` | マーケティング生成ワークフロー |
| `illustration_workflow.py` | 挿絵生成ワークフロー |
| `logical_audit_workflow.py` | 論理的監査ワークフロー |
| `refine_erotic_workflow.py` | エロティック整合性ワークフロー |
| `retry_failed_episodes_workflow.py` | 失敗エピソードリトライワークフロー |
| `commercial_pipeline.py` | 商用展開パイプライン |
| `chapter_import_workflow.py` | 章インポートワークフロー |
| `plan_generation_workflow.py` | 企画生成ワークフロー |
| `quality_metrics.py` | 品質メトリクス計算 |
| `plot_langgraph.py` | LangGraph ベースプロット |
| `writing_langgraph.py` | LangGraph ベース執筆 |
| `graph_state.py` | グラフ状態管理 |
| `dag_builder.py` | DAG ビルダー |
| `_shared_ops.py` | 共有演算ユーティリティ |

### 5.2 修正対象ファイル

- `README.md` §4 (entire section, line 489-612)
- `README.md` §8.1 (line 912-916)

### 5.3 修正内容

#### §4 へのワークフロー層追加

**§4.1 のマルチエージェント図の後、§4.2 の前に以下を追加:**

```markdown
### 4.1.5 ワークフロー層 (Workflows Layer)

`src/backend/workflows/` には、LangGraph ベースのステートグラフワークフローが19種類定義されている。
これらは agents/ と services/ を繋ぐ 중재レイヤーとして機能し、複雑な 멀티エージェント協調を
宣言的に定義する。

| ワークフロー | ファイル | 用途 |
|-------------|----------|------|
| **Easy Mode Workflow** | `easy_mode_workflow.py` | かんたんモードの全体流程管理 |
| **Full Auto Workflow** | `full_auto_workflow.py` | 完全自動執筆の全体流程管理 |
| **Episode Writing Workflow** | `episode_writing_workflow.py` | 単一エピソード執筆流程 |
| **Plot Expansion Workflow** | `plot_expansion_workflow.py` | プロット展開流程 |
| **Plot Rebuild Workflow** | `plot_rebuild_workflow.py` | プロット大規模リビルド |
| **Reverse Plot Workflow** | `reverse_plot_workflow.py` | 逆算プロット生成 |
| **Critique Optimization Workflow** | `critique_optimization_workflow.py` | 批評ベース最適化 |
| **Illustration Workflow** | `illustration_workflow.py` | 挿絵生成流程 |
| **Marketing Generation Workflow** | `marketing_generation_workflow.py` | マーケティング資料生成 |
| **Logical Audit Workflow** | `logical_audit_workflow.py` | 論理的整合性監査 |
| **Refine Erotic Workflow** | `refine_erotic_workflow.py` | エロティック整合性調整 |
| **Retry Failed Episodes Workflow** | `retry_failed_episodes_workflow.py` | 失敗エピソード再実行 |
| **Commercial Pipeline** | `commercial_pipeline.py` | 商用展開統合パイプライン |
| **Chapter Import Workflow** | `chapter_import_workflow.py` | 章インポート流程 |
| **Plan Generation Workflow** | `plan_generation_workflow.py` | 企画生成流程 |
| **Plot LangGraph** | `plot_langgraph.py` | LangGraph プロット状態グラフ |
| **Writing LangGraph** | `writing_langgraph.py` | LangGraph 執筆状態グラフ (32KB) |
| **Quality Metrics** | `quality_metrics.py` | 品質スコアリング算出 |
| **Base Workflow** | `base_workflow.py` | ワークフロー抽象基底クラス |

> **Graph State (`graph_state.py`)**: ワークフロー間の共有グラフ状態管理
> **DAG Builder (`dag_builder.py`)**: ワークフロー DAG 動的構築ユーティリティ
```

#### §8.1 ディレクトリツリー修正 (line 912-916)

**現在:**
```text
│   │   ├── workflows/                 # ステートグラフ / LangGraph ワークフロー
│   │   │   ├── full_auto_workflow.py, easy_mode_workflow.py
│   │   │   ├── episode_writing_workflow.py, plot_expansion_workflow.py
│   │   │   └── illustration_workflow.py, marketing_generation_workflow.py
```

**修正後:**
```text
│   │   ├── workflows/                 # LangGraph ワークフロー (19種類)
│   │   │   ├── base_workflow.py       # ワークフロー抽象基底クラス
│   │   │   ├── easy_mode_workflow.py  # かんたんモード統合ワークフロー
│   │   │   ├── full_auto_workflow.py  # 完全自動執筆ワークフロー
│   │   │   ├── episode_writing_workflow.py  # エピソード執筆ワークフロー
│   │   │   ├── plot_expansion_workflow.py   # プロット展開ワークフロー
│   │   │   ├── plot_rebuild_workflow.py     # プロットリビルドワークフロー
│   │   │   ├── reverse_plot_workflow.py     # 逆算プロットワークフロー
│   │   │   ├── critique_optimization_workflow.py  # 批評最適化ワークフロー
│   │   │   ├── illustration_workflow.py      # 挿絵生成ワークフロー
│   │   │   ├── marketing_generation_workflow.py  # マーケティング生成
│   │   │   ├── logical_audit_workflow.py     # 論理的監査ワークフロー
│   │   │   ├── refine_erotic_workflow.py     # エロティック整合性ワークフロー
│   │   │   ├── retry_failed_episodes_workflow.py  # 失敗リトライ
│   │   │   ├── commercial_pipeline.py   # 商用展開パイプライン
│   │   │   ├── chapter_import_workflow.py  # 章インポートワークフロー
│   │   │   ├── plan_generation_workflow.py  # 企画生成ワークフロー
│   │   │   ├── plot_langgraph.py       # LangGraph プロット状態グラフ
│   │   │   ├── writing_langgraph.py    # LangGraph 執筆状態グラフ
│   │   │   ├── graph_state.py          # グラフ状態管理
│   │   │   ├── dag_builder.py          # DAG ビルダー
│   │   │   ├── quality_metrics.py      # 品質メトリクス計算
│   │   │   ├── _shared_ops.py          # 共有演算ユーティリティ
│   │   │   └── __init__.py
```

---

## 6. 実装順序と依存関係

### Phase 1: P2 修正 (低リスク・小型)

1. **§2.3 フロントエンド component パス修正** → README のみ編集
2. **§3.3 フロントエンド構成セクション修正** → README のみ編集
3. **§3.4 路由器一覧拡充** → README のみ編集
4. **§4.1 EventBus 二重実装文書化** → README のみ編集

### Phase 2: P3 修正 (中型)

5. **§4.1.5 ワークフロー層追加** → 新規セクション作成
6. **§8.1 ディレクトリツリー全面修正** → ツリー構造の更新

### Phase 3: 整合性確認

7. 全文書の相互参照整合性チェック
8. 必要に応じて アーキテクチャ図 (mermaid) の更新

---

## 7. リスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| README 修正による otros への影響 | 低 | 皇帝的変更のみ、意味は保持 |
| ワークフロー説明の正確性 | 中 | 各ワークフローファイルの docstring を参照して正確に記載 |
| 路由器の説明過不足 | 低 | server.py の実装に基づいて説明 |

---

## 8. 完了条件

- [x] README.md §2.3 で `StudioWorkspace.tsx` のパスが `studio/` になっている
- [x] README.md §2.3 で `AssetPackPanel.tsx` が記載されている
- [x] README.md §3.3 でスタジオ/エディタ component が整理されている
- [x] README.md §3.4 で全31路由器が記載されている
- [x] README.md §4.1 で EventBus の2種類が説明されている
- [x] README.md §4.1.5 で19ワークフローが記載されている
- [x] README.md §8.1 でディレクトリ構造が正確に反映されている
- [x] EpisodePipeline のパスが `src/agents/episode_pipeline.py` と記載されている
