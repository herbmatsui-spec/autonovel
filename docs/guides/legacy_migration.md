# レガシー依存性移行ガイド

## ���要

`UltimateHegemonyEngine` クラスには、後方互��性のために残されている非推��プロパティと `_legacy` 経由の依存性注入があります。将来のバージョンではこれらを��除し、明示的な依存性注入（DIコンテナ経由）に統一する予定です。

---

## 非推��プロパティ一覧

| 非推��プロパティ | 移行先 | 備考 |
|----------------|--------|------|
| `engine.ai_api` | `engine.llm` | `FutureWarning` を出力 |
| `engine.llm_client` | `engine.llm` | `FutureWarning` を出力 |
| `engine.logic_validator` | `engine.validator` | エイリアス（警告なし） |
| `engine.planner` / `engine.planning_agent` | DIコンテナ経由で注入 | `_legacy_dep("planner")` 経由 |
| `engine.writer` | DIコンテナ経由で注入 | `_legacy_dep("writer")` 経由 |
| `engine.pm` | DIコンテナ経由で注入 | `_legacy_dep("pm")` 経由 |
| `engine.ctx_mgr` | DIコンテナ経由で注入 | `_legacy_dep("ctx_mgr")` 経由 |
| `engine.formatter` | DIコンテナ経由で注入 | `_legacy_dep("formatter")` 経由 |
| `engine.validator` | DIコンテナ経由で注入 | `_legacy_dep("validator")` 経由 |
| `engine.auditor` | DIコンテナ経由で注入 | `_legacy_dep("auditor")` 経由 |
| `engine.narrative` | DIコンテナ経由で注入 | `_legacy_dep("narrative")` 経由 |
| `engine.critique` | DIコンテナ経由で注入 | `_legacy_dep("critique")` 経由 |
| `engine.marketing` | DIコンテナ経由で注入 | `_legacy_dep("marketing")` 経由 |
| `engine.bible_agent` | DIコンテナ経由で注入 | `_legacy_dep("bible_agent")` 経由 |
| `engine.plot_agent` | DIコンテナ経由で注入 | `_legacy_dep("plot_agent")` 経由 |
| `engine.style_rag` | DIコンテナ経由で注入 | `_legacy_dep("style_rag")` 経由 |

---

## _legacy 経由の依存性注入の仕組み

`UltimateHegemonyEngine` のコンストラクタで `**legacy` として受け取った依存性を、プロパティ経由で��延取得する仕組みです。

```python
def __init__(self, api_key, repo=None, db=None, llm=None, cooldown=None, plot_service=None, **legacy):
    self._legacy = legacy
    # ...

@property
def planner(self):
    return self._legacy_dep("planner")

def _legacy_dep(self, name: str) -> Any:
    if name not in self._legacy:
        raise AttributeError(...)
    return self._legacy[name]
```

DIコンテナ（`src/core/container.py`）では以下のように設定されています：

```python
engine = providers.Factory(
    "src.backend.engine.UltimateHegemonyEngine",
    api_key=api_key,
    planner=planner,           # _legacy["planner"] に注入される
    writer=writer,             # _legacy["writer"] に注入される
    repo=repo,
    db=db,
    pm=pm,                     # _legacy["pm"] に注入される
    ctx_mgr=ctx_mgr,           # _legacy["ctx_mgr"] に注入される
    formatter=formatter,       # _legacy["formatter"] に注入される
    validator=validator,       # _legacy["validator"] に注入される
    auditor=auditor,           # _legacy["auditor"] に注入される
    narrative=narrative,       # _legacy["narrative"] に注入される
    critique=critique,         # _legacy["critique"] に注入される
    marketing=marketing,       # _legacy["marketing"] に注入される
    bible_agent=bible_generator,  # _legacy["bible_agent"] に注入される
    plot_agent=plot_expander,     # _legacy["plot_agent"] に注入される
)
```

---

## 移行手��

### 1. 非推��プロパティの使用��所を特定

```bash
# ai_api / llm_client の使用��所��索
grep -rn "\.ai_api\|\.llm_client" src/ --include="*.py"

# _legacy 経由のプロパティ使用��所��索
grep -rn "engine\.(planner|writer|pm|ctx_mgr|formatter|validator|auditor|narrative|critique|marketing|bible_agent|plot_agent|style_rag)" src/ --include="*.py"
```

### 2. 移行パターン

#### パターンA: 直接プロパティアクセス → DIコンテナ経由

**Before:**
```python
# ワークフロー内で
llm = self.engine.llm  # または self.engine.ai_api (非推��)
```

**After:**
```python
# コンストラクタで明示的に受け取る
def __init__(self, llm: LLMService, ...):
    self.llm = llm

# または DIコンテナから取得
from src.core.container import AppContainer
llm = AppContainer.llm_factory()
```

#### パターンB: base_workflow.py の llm_client 参照修正

**Before:**
```python
self.llm_client = getattr(engine, "llm_client", None) or getattr(engine, "client", None)
```

**After:**
```python
self.llm_client = getattr(engine, "llm", None) or getattr(engine, "client", None)
```

#### パターンC: EngineLLMClient クラスの ai_api 参照

**Before:**
```python
class EngineLLMClient:
    def __init__(self, ai_api: GeminiApiClient):
        self.ai_api = ai_api
```

**After:**
```python
class EngineLLMClient:
    def __init__(self, llm: LLMService):
        self.llm = llm
```

---

## 移行時の注意点

1. **段階的移行**: 一括��除ではなく、警告を出しながら段階的に移行する
2. **テスト実行**: 各移行後に `pytest tests/` を実行して回帰がないか確認
3. **型ヒント追加**: 移行時に型ヒントを明示的に追加すると mypy で��知しやすい

---

## 今後の予定

- v3.3: 非推��プロパティに `FutureWarning` 追加（完了）
- v3.4: 主要な使用��所を DI 経由に移行
- v4.0: 非推��プロパティと `_legacy` 仕組みを完全��除

---

## 関連ファイル

- `src/backend/engine.py` - 非推��プロパティ定義
- `src/core/container.py` - DIコンテナ設定
- `src/backend/workflows/base_workflow.py` - llm_client 参照修正済み
- `src/backend/llm_client.py` - EngineLLMClient クラス（移行候補）
- `src/services/quality_scorer.py` - llm_client パラメータ名（別物、要確認）