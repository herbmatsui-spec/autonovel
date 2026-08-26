# `_legacy` 依存インベントリ

生成日: 2026-08-16
対象: `src/backend/engine.py` の `UltimateHegemonyEngine`

---

## 1. `_legacy` 経由で解決される依存一覧 (12 個)

| # | 依存名 | 実際のクラス | プロパティ経由でのアクセス箇所 |
|---|--------|-------------|--------------------------|
| 1 | `planner` | `src.agents.PlanningAgent` | `engine.planner` / `engine.planning_agent` |
| 2 | `writer` | `src.agents.WritingAgent` | `engine.writer` |
| 3 | `pm` | `prompts.manager.PromptManager` | `engine.pm` |
| 4 | `ctx_mgr` | `src.backend.engine_context.ContextManager` | `engine.ctx_mgr` |
| 5 | `formatter` | `src.backend.sanitizer.TextFormatter` | `engine.formatter` |
| 6 | `validator` | `src.agents.audit.LogicalAuditor` | `engine.validator` / `engine.logic_validator` |
| 7 | `auditor` | `src.agents.audit.LogicalAuditor` | `engine.auditor` |
| 8 | `narrative` | `src.backend.engine_narrative.NarrativeController` | `engine.narrative` |
| 9 | `critique` | `src.backend.engine_critique.CritiqueAgent` | `engine.critique` |
| 10 | `marketing` | `src.agents.MarketingAgent` | `engine.marketing` |
| 11 | `bible_agent` | `src.services.bible_service.WorldBibleGenerator` | `engine.bible_agent` |
| 12 | `plot_agent` | `src.agents.plot.PlotAgent` | `engine.plot_agent` |
| 13 | `style_rag` | `src.backend.engine_style_rag.StyleRagManager` | `engine.style_rag` |

※ `planner` と `planning_agent` は同一依存

---

## 2. 依存の注入経路

### AppContainer2 で定義済み（13個中 12個）

```python
# app.py で定義済み
planner = providers.Singleton["PlanningAgent"](...)
writer = providers.Singleton["WritingAgent"](...)
pm = providers.Singleton["PromptManager"](...)
ctx_mgr = providers.Singleton(ContextManager, ...)
auditor = providers.Singleton["LogicalAuditor"](...)
marketing = providers.Singleton["MarketingAgent"](...)
bible_generator = providers.Singleton["WorldBibleGenerator"](...)
plot_expander = providers.Singleton["PlotAgent"](...)
validator = providers.Singleton["LogicalAuditor"](...)
narrative = providers.Singleton["NarrativeController"](...)
critique = providers.Singleton["CritiqueAgent"](...)
style_rag = providers.Singleton["StyleRagManager"](...)
formatter = providers.Singleton["TextFormatter"](...)
```

### engine プロバイダで注入されているもの（6個のみ）

```python
engine = providers.Factory["UltimateHegemonyEngine"](
    "src.backend.engine.UltimateHegemonyEngine",
    api_key=api_key,
    repo=repo,
    db=InfraContainer.db,
    llm=llm,
    cooldown=InfraContainer.cooldown,
    plot_service=plot_service,
    # 残り12個は **legacy 経由で渡される想定だが、現状は渡されていない
)
```

**問題**: `AppContainer2` には依存が定義されているが、`engine` プロバイダではそれらを渡していない。

---

## 3. 呼び出し側の影響範囲

### EngineFacade 経由（全プロパティ委譲）

`src/backend/engine_facade.py` で全 17 プロパティを委譲:
- `pm`, `ctx_mgr`, `formatter`, `validator`, `auditor`, `narrative`, `critique`, `marketing`, `bible_agent`, `plot_agent`, `style_rag`, `planner`, `writer`, `plot_service`, `logic_validator`, `generate_json`, `db`

### Workflows 直接アクセス

| ファイル | アクセスするプロパティ |
|---------|---------------------|
| `src/backend/workflows/plot_langgraph.py` | `pm`, `ctx_mgr`, `auditor`, `narrative` |
| `src/backend/workflows/plot_expansion_workflow.py` | `planner` |
| `src/backend/workflows/plot_rebuild_workflow.py` | `planner`, `plot_agent` |
| `src/backend/workflows/logical_audit_workflow.py` | `auditor` |
| `src/backend/workflows/plan_generation_workflow.py` | `planner` |
| `src/backend/workflows/full_auto_workflow.py` | `planner`, `plan_auditor` |
| `src/backend/workflows/base_workflow.py` | `planner`, `writer`, `critique`, `narrative`, `marketing`, `bible_agent`, `plot_agent`, `formatter` (フォールバック) |

### Routers 直接アクセス

| ファイル | アクセスするプロパティ |
|---------|---------------------|
| `src/backend/routers/plots.py` | `engine.planner.audit_producer_plan` |
| `src/backend/routers/marketing.py` | `engine.marketing.create_export_package` |

### Services 経由（DI 推奨）

| サービス | 注入される依存 |
|---------|--------------|
| `PlanningService` | `pm`, `ctx_mgr` |
| `CritiqueService` | `critique`, `pm` |
| `WritingService` | `writer`, `pm`, `style_rag`, `ctx_mgr` |
| `NarrativeController` | `pm`, `ctx_mgr`, `auditor` |

---

## 4. 新コンストラクタに必要な引数

```python
def __init__(
    self,
    api_key: str,
    repo: DataRepository,
    db: DatabaseManager,
    llm: LLMGenerateResultProxy,
    cooldown: AdaptiveCooldown,
    plot_service: PlotService,
    # 以下を追加
    planner: PlanningAgent,
    writer: WritingAgent,
    pm: PromptManager,
    ctx_mgr: ContextManager,
    formatter: TextFormatter,
    validator: LogicalAuditor,
    auditor: LogicalAuditor,
    narrative: NarrativeController,
    critique: CritiqueAgent,
    marketing: MarketingAgent,
    bible_agent: WorldBibleGenerator,
    plot_agent: PlotAgent,
    style_rag: StyleRagManager,
    **legacy: Any,  # 後方互換（DeprecationWarning）
) -> None:
```

---

## 5. 次のアクション

1. **Step 3**: 新コンストラクタ仕様書作成 (`proposals/engine_refactor_spec.md`)
2. **Step 4**: `engine.py` の `__init__` 修正
3. **Step 5**: プロパティ群を新属性アクセスに変更（フォールバック付き）
4. **Step 6**: `AppContainer2.engine` プロバイダに全依存を追加
5. **Step 7**: 単体テスト追加

---

## 6. リスク評価

| リスク | 影響度 | 対策 |
|--------|--------|------|
| 既存コードが `engine._legacy` 直接アクセス | 低 | grep 確認済み、直接アクセスなし |
| `EngineFacade` 経由の委譲が壊れる | 高 | プロパティ名変更なし、内部実装のみ変更 |
| Workflows が直接 `engine.xxx` 参照 | 中 | ファサード経由移行は別 Phase、今回は互換維持 |
| 循環依存（engine → planner → engine 等） | 中 | コンテナで Singleton 管理、遅延評価で回避可能 |