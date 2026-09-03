# AutoNovel アーキテクチャ設計書

> マルチエージェントオーケストレーションを中心としたシステムアーキテクチャ

## 1. 概要

AutoNovel は 8 つの特化エージェントを **Orchestrator** で順序実行することで、長編小説の自動制作を実現します。本書ではエージェント層、制御フロー、観測性、easy_mode との違いを記述します。

---

## 2. コアコンポーネント

### 2.1 クラス図

```
┌─────────────────────────────────────────────────────────────────┐
│                         Orchestrator                            │
│  - nodes: dict[AgentName, AgentNode]                            │
│  - event_bus: Optional[EventBus]                                │
│  - correlation_id: Optional[str]                                │
│                                                                  │
│  + run(ctx, start) -> AgentContext                              │
└─────────────────────────────────────────────────────────────────┘
                                │ 1:N
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AgentNode (Callable)                          │
│         async (ctx: AgentContext) -> AgentResult                 │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                       BaseAgent (ABC)                           │
│  + run(ctx) -> AgentResult    # 抽象メソッド                    │
│  + repo, llm, style_rag, rag_prefetch                          │
└─────────────────────────────────────────────────────────────────┘
                                ▲
        ┌────────┬────────┬────────┬────────┬────────┬────────┐
        │Planning│  Plot  │ Bible  │Context │Writing │  ...   │
        │ Agent  │ Agent  │ Agent  │Builder │ Agent  │  ...   │
        └────────┴────────┴────────┴────────┴────────┴────────┘
```

### 2.2 データモデル

```
┌─────────────────────────────────────────┐
│            AgentContext                  │
│  - book_id: int                          │
│  - branch_id: int                        │
│  - ep_num: int                           │
│  - artifacts: dict[str, Any]            │ ← 共有キーバリューストア
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│            AgentResult                   │
│  - next_agent: AgentName | None          │
│  - artifacts: dict[str, Any]            │ ← 当該エージェントの成果物
│  - should_retry: bool                    │
│  - error: str | None                     │
└─────────────────────────────────────────┘

┌─────────────────────────────────────────┐
│             AgentEvent                   │
│  - agent: str                            │ ← "planning", "plot", ...
│  - payload: dict[str, Any]              │
│  - correlation_id: str                   │ ← トレーシング用
└─────────────────────────────────────────┘
```

---

## 3. 8 エージェント構成

| エージェント | 役割 | 入力 | 出力 |
|:---|:---|:---|:---|
| **PlanningAgent** | アーク・全体プロット生成 | `title`, `synopsis`, `target_eps` | `arcs` |
| **PlotAgent** | エピソード単位プロット展開 | `arcs`, `ep_num` | `plots` |
| **BibleAgent** | 世界観・キャラクター設定生成 | `title`, `genre`, `keywords` | `bible` |
| **ContextBuilderAgent** | 執筆用コンテキスト構築 | `repo`, `bible`, `plots`, `prev_chapter` | `writing_context` |
| **WritingAgent** | エピソード本文生成 | `writing_context` | `drafted_text` |
| **AuditAgent** | 品質監査 (論理/DeAI/能力/因果) | `writing_context`, `drafted_text` | `audit_report` (合格/不合格) |
| **IllustrationAgent** | 挿絵プロンプト生成 | `drafted_text`, `book_context` | `illustrations` |
| **MarketingAgent** | 納品パッケージ ZIP 生成 | 全成果物 | `zip_data`, `zip_filename` |

---

## 4. 制御フロー

### 4.1 正常系

```
PLANNING → PLOT → BIBLE → CONTEXT_BUILDER → WRITING → AUDIT → ILLUSTRATION → MARKETING → 終了
```

### 4.2 リトライ系（AuditAgent 不合格時）

```
WRITING → AUDIT (不合格) → should_retry=true → WRITING (再実行) → AUDIT (合格) → ILLUSTRATION → ...
```

### 4.3 Orchestrator 状態遷移

```python
current = start
while current:
    event_bus.publish(started)
    result = await nodes[current](ctx)
    event_bus.publish(completed)
    ctx.artifacts.update(result.artifacts)
    if result.should_retry:
        continue
    if result.error:
        raise RuntimeError
    current = result.next_agent  # None なら終了
```

---

## 5. 観測性（EventBus）

### 5.1 インメモリモード（デフォルト）

```
Orchestrator ──publish()──> EventBus
                              │
                              ├─→ LocalHandler (asyncio task)
                              └─→ Logger
```

- 同一プロセス内で動作
- テスト・開発環境向け
- 依存ゼロ・標準ライブラリのみ

### 5.2 Redis Streams モード（本番）

```
Orchestrator ──XADD──> Redis Stream (agent_events:{correlation_id})
                                                    │
                                                    ▼
                                          XREADGROUP (consumer group)
                                                    │
                            ┌───────────────────────┼───────────────────────┐
                            ▼                       ▼                       ▼
                     MetricsCollector      AlertingService        AuditLogger
```

**有効化**:
```bash
USE_REDIS_EVENTS=true
REDIS_URL=redis://redis:6379/0
```

**コンシューマー例** (`scripts/consume_events.py`):
```python
XREADGROUP CONSUMER_GROUP CONSUMER_NAME {stream_name: ">"} BLOCK 5000
```

---

## 6. easy_mode との比較

| 観点 | easy_mode | orchestrated |
|:---|:---|:---|
| **エントリポイント** | `POST /easy_mode/generate` | `POST /orchestrated/generate` |
| **実行モデル** | 単一関数 (`generate_with_llm`) | Orchestrator + 8 ノード |
| **タスク実装** | `generate_chapter_task` | `generate_chapter_orchestrated_task` |
| **リトライ** | 内部ループのみ | `AgentResult.should_retry` による宣言的リトライ |
| **観測性** | ログのみ | EventBus による構造化イベント |
| **対象ユーザー** | ライト層（かんたんモード） | パワーユーザー（詳細制御） |
| **LLM 呼び出し** | 1〜2 回 | 8 回（各エージェント） |
| **所要時間** | 数十秒 | 数分 |

両モードは **同一 Huey キュー / DB スキーマ / 依存サービス** を共有し、競合しない。

---

## 7. デプロイメントアーキテクチャ

```
┌────────────────────────────────────────────────────────────┐
│                        Docker Compose                       │
│                                                             │
│  ┌─────────┐    ┌──────────┐    ┌──────────────┐          │
│  │ backend │    │  worker  │    │  consumer    │          │
│  │ (uvicorn)│───>│ (huey)   │    │ (events)     │ ← NEW   │
│  └────┬────┘    └────┬─────┘    └──────┬───────┘          │
│       │              │                 │                   │
│       └──────────────┼─────────────────┘                   │
│                      │                                     │
│              ┌───────▼────────┐                            │
│              │     Redis       │ ← キュー + Streams        │
│              │  ┌───────────┐  │                            │
│              │  │ Huey Queue │  │                            │
│              │  │  Streams   │  │                            │
│              │  └───────────┘  │                            │
│              └────────────────┘                            │
│                      │                                     │
│              ┌───────▼────────┐                            │
│              │   PostgreSQL    │                            │
│              │ (pgvector+AGE)  │                            │
│              └─────────────────┘                            │
└────────────────────────────────────────────────────────────┘
```

---

## 8. 拡張パターン

### 8.1 並列エージェント実行

Orchestrator は現状逐次実行のみ。将来的に `AgentResult.next_agent` を **複数指定可能なタプル/リスト** に拡張することで並列実行が可能：

```python
# 将来案
@dataclass
class AgentResult:
    next_agents: list[AgentName] = field(default_factory=list)  # 並列実行
```

### 8.2 条件分岐

`AgentResult.next_agent` を `Callable[[AgentContext], AgentName | None]` に変更することで、動的ルーティングが可能。

### 8.3 永続化

`EventBus` を永続化（PostgreSQL 等の EventStore）に変更することで、リプレイ/デバッグが可能。

---

## 9. テスト戦略

| レイヤー | テストファイル | カバー範囲 |
|:---|:---|:---|
| 単体 | `tests/unit/` | 各エージェント・ユーティリティ |
| 統合 | `tests/integration/test_full_pipeline.py` | 8 エージェント一気通し・EventBus・Retry |
| API | `tests/integration/test_orchestrated_api.py` | `/orchestrated/*` エンドポイント |
| パフォーマ