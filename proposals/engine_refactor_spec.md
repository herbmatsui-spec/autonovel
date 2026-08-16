# `UltimateHegemonyEngine` リファクタ仕様書

作成日: 2026-08-16
対象: `src/backend/engine.py`

---

## 1. 現状の問題

- `__init__` が 7 個の明示引数 + `**legacy` (12個の隠れ依存) を受け取る
- `_legacy_dep()` でランタイム解決 → 型安全性なし、循環依存リスク、テスト困難
- `EngineFacade` が全プロパティを委譲しているが、実体は `_legacy` 経由

---

## 2. 新コンストラクタ仕様

### 2.1 シグネチャ

```python
def __init__(
    self,
    api_key: str,
    repo: "DataRepository",
    db: "DatabaseManager",
    llm: "LLMGenerateResultProxy",
    cooldown: "AdaptiveCooldown",
    plot_service: "PlotService",
    # 以下を新規追加（全て Optional で後方互換）
    planner: Optional["PlanningAgent"] = None,
    writer: Optional["WritingAgent"] = None,
    pm: Optional["PromptManager"] = None,
    ctx_mgr: Optional["ContextManager"] = None,
    formatter: Optional["TextFormatter"] = None,
    validator: Optional["LogicalAuditor"] = None,
    auditor: Optional["LogicalAuditor"] = None,
    narrative: Optional["NarrativeController"] = None,
    critique: Optional["CritiqueAgent"] = None,
    marketing: Optional["MarketingAgent"] = None,
    bible_agent: Optional["WorldBibleGenerator"] = None,
    plot_agent: Optional["PlotAgent"] = None,
    style_rag: Optional["StyleRagManager"] = None,
    **legacy: Any,
) -> None:
```

### 2.2 設計方針

1. **全依存を明示的引数化** - `Optional` でデフォルト `None`、後方互換維持
2. **`**legacy` は維持** - 既存コードが `_legacy` 辞書で渡しても動作するよう `DeprecationWarning` 発行
3. **属性への直接代入** - `self.planner = planner` 等で保持
4. **プロパティは新属性を返す** - `_legacy_dep` はフォールバックのみに縮小

---

## 3. プロパティ実装方針

### 3.1 新実装パターン

```python
# 旧: @property で _legacy_dep 呼び出し
@property
def planner(self) -> "PlanningAgent":
    return self._legacy_dep("planner")

# 新: 直接属性アクセス、未設定なら _legacy_dep にフォールバック
@property
def planner(self) -> "PlanningAgent":
    if self._planner is not None:
        return self._planner
    return self._legacy_dep("planner")
```

### 3.2 対象プロパティ (13個 + エイリアス 2個)

| プロパティ | 内部属性 | エイリアス |
|-----------|---------|-----------|
| `planner` | `_planner` | `planning_agent` |
| `writer` | `_writer` | - |
| `pm` | `_pm` | - |
| `ctx_mgr` | `_ctx_mgr` | - |
| `formatter` | `_formatter` | - |
| `validator` | `_validator` | `logic_validator` |
| `auditor` | `_auditor` | - |
| `narrative` | `_narrative` | - |
| `critique` | `_critique` | - |
| `marketing` | `_marketing` | - |
| `bible_agent` | `_bible_agent` | - |
| `plot_agent` | `_plot_agent` | - |
| `style_rag` | `_style_rag` | - |

### 3.3 維持する非推奨プロパティ

- `ai_api` → `FutureWarning` 発行、`self.llm` を返す
- `llm_client` → `FutureWarning` 発行、`self.llm` を返す

---

## 4. `_legacy_dep` メソッドの縮小

```python
def _legacy_dep(self, name: str) -> Any:
    """後方互換: _legacy 辞書から依存を取得（非推奨）"""
    import warnings
    warnings.warn(
        f"_legacy_dep('{name}') is deprecated. Pass '{name}' explicitly to constructor.",
        DeprecationWarning,
        stacklevel=2,
    )
    if name not in self._legacy:
        raise AttributeError(
            f"'{self.__class__.__name__}' has no legacy dependency '{name}'. "
            "Inject it via constructor or upgrade the caller."
        )
    return self._legacy[name]
```

---

## 5. 移行手順

### Step 4: `engine.py` 修正
1. `__init__` シグネチャ拡張
2. 全引数を `self._xxx = xxx` で保存
3. `self._legacy = legacy` 維持
4. 全 `@property` を新パターンに変更

### Step 5: `AppContainer2.engine` 修正
```python
engine = providers.Factory["UltimateHegemonyEngine"](
    "src.backend.engine.UltimateHegemonyEngine",
    api_key=api_key,
    repo=repo,
    db=InfraContainer.db,
    llm=llm,
    cooldown=InfraContainer.cooldown,
    plot_service=plot_service,
    # 以下を追加
    planner=planner,
    writer=writer,
    pm=pm,
    ctx_mgr=ctx_mgr,
    formatter=formatter,
    validator=validator,
    auditor=auditor,
    narrative=narrative,
    critique=critique,
    marketing=marketing,
    bible_agent=bible_generator,
    plot_agent=plot_expander,
    style_rag=style_rag,
)
```

### Step 6: テスト追加
- 新コンストラクタでのインスタンス化テスト
- `None` 渡しでのフォールバックテスト
- `DeprecationWarning` 発火テスト

---

## 6. 型ヒントのインポート戦略

`TYPE_CHECKING` ブロックで循環インポート回避:

```python
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from src.backend.database import DataRepository
    from src.backend.database.core import DatabaseManager
    from src.backend.engine_config import EngineConfig
    from src.core.llm_gateway import LLMGenerateResultProxy
    from src.backend.engine_utils import AdaptiveCooldown
    from src.services.plot_service import PlotService
    from src.agents.PlanningAgent import PlanningAgent
    from src.agents.WritingAgent import WritingAgent
    from prompts.manager import PromptManager
    from src.backend.engine_context import ContextManager
    from src.backend.sanitizer import TextFormatter
    from src.agents.audit import LogicalAuditor
    from src.backend.engine_narrative import NarrativeController
    from src.backend.engine_critique import CritiqueAgent
    from src.agents.MarketingAgent import MarketingAgent
    from src.services.bible_service import WorldBibleGenerator
    from src.agents.plot import PlotAgent
    from src.backend.engine_style_rag import StyleRagManager
```

---

## 7. 完了基準

- [ ] `mypy --strict src/backend/engine.py` エラー 0 件
- [ ] 既存テスト `pytest tests/ -x` 全 PASS
- [ ] `EngineFacade` 経由の全プロパティアクセスが動作
- [ ] `DeprecationWarning` が適切に発火（`legacy` 使用時のみ）
- [ ] 新コンストラクタで全依存渡し時、`_legacy_dep` が呼ばれない