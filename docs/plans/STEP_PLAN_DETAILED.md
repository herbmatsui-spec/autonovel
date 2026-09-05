# 統合パイプライン実装計画 (Step A-J)

## 全体方針

REMAINING_IMPLEMENTATION_PLAN.md で定義された Step 9-36 のうち、**Step 9-23 (委譲本体) は既に完了**しているが、以下の不整合と残作業がある。

### 現状の不整合 (要修正)

| 場所 | 現状 | 問題 |
|------|------|------|
| `easy_mode_workflow.py:76` | `UnifiedProgressReporter(reporter=reporter)` | FullAuto は `ProgressReporterAdapter` を使用しており、Adapter クラスが2つ混在 |
| `auto_workflow_pipeline.py:74` | `adapter = ProgressReporterAdapter(reporter, ctx.is_easy_mode)` | ワークフローから渡された adapter 変数を再 wrap する冗長構造 |
| `full_auto_workflow.py:34-37`, `easy_mode_workflow.py:49-52` | `USE_UNIFIED=False` でも unified pipeline を使用 | フラグ切替が無意味 |

### 確認済み事項

- `src/easy_mode/pipeline.py` の旧実装は削除済み
- `tests/test_unified_pipeline.py` の 26 テストはすべて pass
- `FullAutoWorkflow` / `EasyModeWorkflow` は既に `AutoWorkflowPipeline` に委譲済み

---

## Step A: EasyModeWorkflow の Adapter を統一 [HIGH]

### 目的
Adapter クラスの不整合を解消し、FullAutoWorkflow / EasyModeWorkflow で同じ API を使う。

### 修正対象
`src/backend/workflows/easy_mode_workflow.py`

### 変更内容
```python
# 修正前 (line 21, 76)
from src.services.progress_reporter import UnifiedProgressReporter
adapter = UnifiedProgressReporter(reporter=reporter)

# 修正後
from src.services.progress_reporter import ProgressReporterAdapter
adapter = ProgressReporterAdapter(reporter, is_easy_mode=True)
```

### 確認コマンド
```bash
python -c "from src.backend.workflows.easy_mode_workflow import EasyModeWorkflow; import inspect; src=inspect.getsource(EasyModeWorkflow.execute); assert 'ProgressReporterAdapter' in src; print('OK')"
```

### 影響範囲
EasyModeWorkflow のみ。機能上の影響はなし（UnifiedProgressReporter と ProgressReporterAdapter は同じインターフェースを持つ）。

---

## Step B: AutoWorkflowPipeline.execute() の重複 wrap 解消 [HIGH]

### 目的
`pipeline.execute()` 内で受け取った reporter を再 wrap している冗長コードを解消する。

### 現状の問題
```python
# src/services/auto_workflow_pipeline.py:71-75
async def execute(
    self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter
) -> FullAutoWorkflowResult:
    adapter = ProgressReporterAdapter(reporter, ctx.is_easy_mode)
    adapter.report("🚀 全自動モード開始！", "info")
```

`reporter` 引数の型が `StatusReporter` だが、実態はワークフローが渡した Adapter。型と実装が乖離している。

### 修正方針 (2案)

**案1 (推奨)**: Adapter を受け取らない、直接 `StatusReporter` を使ってステップ実行
- メリット: 型整合、コードがシンプル
- デメリット: 既存テスト (`test_unified_pipeline.py`) の修正が必要

**案2**: Adapter を型として明示、ワークフローと統一
- メリット: 既存テストへの影響なし
- デメリット: 型追加の必要性

**推奨案1の詳細**:

```python
# src/services/auto_workflow_pipeline.py
from src.services.progress_reporter import ProgressReporterAdapter

class AutoWorkflowPipeline:
    def __init__(self, steps: list[WorkflowStep]):
        self.steps = steps

    async def execute(
        self, ctx: WorkflowContext, engine: UltimateHegemonyEngine, reporter: StatusReporter
    ) -> FullAutoWorkflowResult:
        # StatusReporter を Adapter で wrap (ProgressReporterAdapter が reporter interface を提供)
        adapter: StatusReporter = ProgressReporterAdapter(reporter, ctx.is_easy_mode)
        adapter.report("🚀 全自動モード開始！", "info")
        # ... 以下同じ
```

### 確認コマンド
```bash
pytest tests/test_unified_pipeline.py -v --tb=short -p no:cacheprovider
```

---

## Step C: EasyModeWorkflow テスト作成 [HIGH]

### 目的
EasyModeWorkflow → 統合パイプライン委譲の単体テストを追加。

### 新規ファイル
`tests/test_easy_mode_workflow.py`

### テストケース

```python
"""EasyModeWorkflow → AutoWorkflowPipeline 委譲テスト"""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from src.services.pipeline_base import WorkflowContext


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.planner = MagicMock()
    engine.planner.infer_easy_mode_params = AsyncMock(...)
    # ... 他の必要なモック
    return engine


@pytest.fixture
def mock_reporter():
    reporter = MagicMock()
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    reporter.state = MagicMock(should_stop=lambda: False)
    return reporter


@pytest.mark.asyncio
async def test_easy_mode_delegates_to_pipeline(mock_engine, mock_reporter):
    """EasyModeWorkflow.execute() が AutoWorkflowPipeline に委譲することを確認"""
    from src.backend.workflows.easy_mode_workflow import EasyModeWorkflow

    workflow = EasyModeWorkflow(engine=mock_engine)
    with patch("src.backend.workflows.easy_mode_workflow.create_easy_mode_pipeline") as mock_create:
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=MagicMock(
            book_id=1, title="test", chars_count=1000,
            status="success", easy_parameters={},
            average_audit_score=85.0, episodes_detail=[],
        ))
        mock_create.return_value = mock_pipeline

        result = await workflow.execute(
            mock_reporter,
            genre="ファンタジー",
            keywords=["test"],
            protagonist_type="チート",
            target_episodes=3,
        )

    # AutoWorkflowPipeline.execute が呼ばれたことを確認
    assert mock_pipeline.execute.await_count == 1
    # is_easy_mode=True の Context で呼ばれた
    call_args = mock_pipeline.execute.await_args
    ctx = call_args.args[0]
    assert ctx.is_easy_mode is True
    assert ctx.genre == "ファンタジー"


@pytest.mark.asyncio
async def test_easy_mode_uses_progress_reporter_adapter(mock_engine, mock_reporter):
    """Adapter として ProgressReporterAdapter が使われることを確認"""
    from src.backend.workflows.easy_mode_workflow import EasyModeWorkflow
    from src.services.progress_reporter import ProgressReporterAdapter

    workflow = EasyModeWorkflow(engine=mock_engine)
    with patch("src.backend.workflows.easy_mode_workflow.create_easy_mode_pipeline") as mock_create, \
         patch("src.backend.workflows.easy_mode_workflow.ProgressReporterAdapter", wraps=ProgressReporterAdapter) as mock_adapter_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=MagicMock(
            book_id=1, status="success", easy_parameters={}, average_audit_score=0,
            episodes_detail=[], illustrations=[], marketing_pack=None,
            chars_count=0, title="", failed_episodes=[],
        ))
        mock_create.return_value = mock_pipeline

        await workflow.execute(mock_reporter, genre="ファンタジー")

        # is_easy_mode=True で Adapter 作成
        mock_adapter_cls.assert_called_once()
        kwargs = mock_adapter_cls.call_args.kwargs or mock_adapter_cls.call_args.args
        # is_easy_mode=True 確認
        # ...
```

### 確認コマンド
```bash
pytest tests/test_easy_mode_workflow.py -v --tb=short -p no:cacheprovider
```

---

## Step D: FullAutoWorkflow テスト作成 [HIGH]

### 目的
FullAutoWorkflow → 統合パイプライン委譲の単体テストを追加。

### 新規ファイル
`tests/test_full_auto_workflow.py`

### テストケース

```python
"""FullAutoWorkflow → AutoWorkflowPipeline 委譲テスト"""
from unittest.mock import AsyncMock, MagicMock, patch
import pytest


@pytest.fixture
def mock_engine():
    return MagicMock()


@pytest.fixture
def mock_reporter():
    reporter = MagicMock()
    reporter.update_progress = MagicMock()
    reporter.report = MagicMock()
    reporter.state = MagicMock(should_stop=lambda: False)
    return reporter


@pytest.mark.asyncio
async def test_full_auto_delegates_to_pipeline(mock_engine, mock_reporter):
    """FullAutoWorkflow.execute() が AutoWorkflowPipeline に委譲することを確認"""
    from src.backend.workflows.full_auto_workflow import FullAutoWorkflow

    workflow = FullAutoWorkflow(engine=mock_engine)
    with patch("src.backend.workflows.full_auto_workflow.create_full_auto_pipeline") as mock_create:
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=MagicMock(
            book_id=1, title="test", chars_count=1000, status="success",
            easy_parameters={}, average_audit_score=85.0, episodes_detail=[],
            zip_data=None, zip_filename=None, illustrations=[], marketing_pack=None,
            failed_episodes=[],
        ))
        mock_create.return_value = mock_pipeline

        result = await workflow.execute(
            mock_reporter,
            genre="ファンタジー",
            keywords=["test"],
            archetype_key="王道",
            target_eps=3,
            initial_limit=3,
            word_count=2000,
        )

    mock_pipeline.execute.assert_awaited_once()
    call_args = mock_pipeline.execute.await_args
    ctx = call_args.args[0]
    assert ctx.is_easy_mode is False
    assert ctx.genre == "ファンタジー"


@pytest.mark.asyncio
async def test_full_auto_uses_progress_reporter_adapter(mock_engine, mock_reporter):
    """is_easy_mode=False で ProgressReporterAdapter 作成"""
    from src.backend.workflows.full_auto_workflow import FullAutoWorkflow

    workflow = FullAutoWorkflow(engine=mock_engine)
    with patch("src.backend.workflows.full_auto_workflow.create_full_auto_pipeline") as mock_create, \
         patch("src.backend.workflows.full_auto_workflow.ProgressReporterAdapter") as mock_adapter_cls:
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=MagicMock(
            book_id=1, status="success", easy_parameters={}, average_audit_score=0,
            episodes_detail=[], zip_data=None, zip_filename=None,
            illustrations=[], marketing_pack=None, chars_count=0, title="",
            failed_episodes=[],
        ))
        mock_create.return_value = mock_pipeline

        await workflow.execute(
            mock_reporter,
            genre="ファンタジー",
            keywords=["test"],
            archetype_key="王道",
            target_eps=3,
            initial_limit=3,
            word_count=2000,
        )

        # is_easy_mode=False で Adapter 作成
        mock_adapter_cls.assert_called_once_with(mock_reporter, is_easy_mode=False)
```

### 確認コマンド
```bash
pytest tests/test_full_auto_workflow.py -v --tb=short -p no:cacheprovider
```

---

## Step E: 全テストスイート実行 [HIGH]

### 目的
リグレッションゼロを確認。

### 実行コマンド
```bash
cd /home/herbmatsui/autonovel
pytest tests/ -v --tb=short -p no:cacheprovider --no-cov > /tmp/all_tests.log 2>&1
```

### 目標
- 0 failures
- 既存 26 テスト含めて維持
- 新規 Step C/D のテスト追加分も pass

### 失敗時の対応
1. ログ末尾で `FAILED` ファイルを特定
2. 各失敗テストを個別実行して詳細確認
3. Adapter 統一やマッパー修正でリカバリ

---

## Step F: ruff check + 未使用 import 削除 [MEDIUM]

### 目的
コード品質の最終チェック。

### 確認コマンド
```bash
cd /home/herbmatsui/autonovel
ruff check src/ --select F401  # 未使用 import
ruff check src/  # 全ルール
```

### 期待される検出項目 (候補)
- `src/services/auto_workflow_pipeline.py:11` `ProgressReporterAdapter` の import (Step B 修正後)
- `src/services/progress_reporter.py:30` `UnifiedProgressReporter` クラス自体 (Step A 完了後、使用箇所がなくなる場合)
- `src/services/progress_reporter.py:114` `StatusReporterAdapter` (使用箇所確認)

### 削除判断基準
- `grep -r "UnifiedProgressReporter" src/ tests/` で使用箇所ゼロなら削除
- 他の Adapter クラスも同様

---

## Step G: mypy 型エラー修正 [MEDIUM]

### 目的
`Step B` の型整合修正後に発生する可能性のある型エラーを解消。

### 実行コマンド
```bash
cd /home/herbmatsui/autonovel
mypy src/services/auto_workflow_pipeline.py
mypy src/services/progress_reporter.py
mypy src/backend/workflows/full_auto_workflow.py
mypy src/backend/workflows/easy_mode_workflow.py
```

### 期待される修正
- `ProgressReporterAdapter(reporter: Any, ...)` の `reporter` 型を `StatusReporter` に変更
- `pipeline.execute()` の `reporter` 引数型と整合

---

## Step H: USE_UNIFIED_PIPELINE フラグの正式実装 [MEDIUM]

### 現状の問題
- `USE_UNIFIED_PIPELINE=0` にしても警告ログのみで実動作は unified pipeline のまま
- 旧実装は削除済みなので切替不能

### 実装方針

#### H-1: フラグを完全削除 (推奨)

**理由**:
- 旧実装 (`src/easy_mode/pipeline.py`) は既に削除済み
- フラグを残しても切替先がない
- YAGNI 原則: 必要になったら追加する方が安全

**変更内容**:
```python
# full_auto_workflow.py / easy_mode_workflow.py から以下を削除
import os
USE_UNIFIED = os.getenv("USE_UNIFIED_PIPELINE", "1") == "1"

if not USE_UNIFIED:
    logger.warning(...)
```

#### H-2: フラグを残す場合

**変更内容**:
```python
USE_UNIFIED = os.getenv("USE_UNIFIED_PIPELINE", "1") == "1"
# フラグ False 時は NotImplementedError で明示的にエラー
if not USE_UNIFIED:
    raise NotImplementedError(
        "USE_UNIFIED_PIPELINE=0 is not supported. The old implementation was removed."
    )
```

### 推奨判断
**H-1 推奨**: 旧実装削除済みなので、フラグを残すと混乱の元。完全削除が最適。

---

## Step I: ドキュメント更新 [MEDIUM]

### 更新対象

1. **AGENTS.md**
   - アーキテクチャ図に `AutoWorkflowPipeline` を追加
   - "FullAutoWorkflow / EasyModeWorkflow → AutoWorkflowPipeline" の委譲関係を明記
   - `src/services/pipeline_*.py` 群の説明追加

2. **CHANGELOG.md**
   - 統合パイプライン実装完了エントリ追加
   - 例: `[2026-09-04] PipelineUnification - FullAutoWorkflow/EasyModeWorkflow を AutoWorkflowPipeline に統合`

3. **PIPELINE_UNIFICATION_PLAN.md**
   - 冒頭に `[STATUS: COMPLETED 2026-09-04]` 追加
   - 全 Step の横に `[x]` チェックマーク

4. **REMAINING_IMPLEMENTATION_PLAN.md**
   - 冒頭に `[STATUS: SUPERSEDED]` 追加
   - 「このドキュメントは新計画 STEP_PLAN_DETAILED.md に置き換えられました」

### 確認コマンド
```bash
ls AGENTS.md CHANGELOG.md PIPELINE_UNIFICATION_PLAN.md REMAINING_IMPLEMENTATION_PLAN.md
```

---

## Step J: 旧計画の DEPRECATED 化 [LOW]

### 変更内容

#### `REMAINING_IMPLEMENTATION_PLAN.md` の冒頭
```markdown
# ⚠️ DEPRECATED (2026-09-04)

このドキュメントは **完了済み** です。実装の現状は以下を参照：
- コード: `src/backend/workflows/{full,easy_mode}_workflow.py`
- テスト: `tests/test_unified_pipeline.py` (26 テスト pass)
- 新計画: STEP_PLAN_DETAILED.md (本ファイル)
```

#### `IMPLEMENTATION_PLAN_REMAINING.md` も同様

#### `REMAINING_STEPS_PLAN.md` も同様 (存在する場合)

---

## 実行順序と所要時間見積もり

| Step | 内容 | 優先度 | 推定工数 |
|------|------|--------|----------|
| A | EasyMode Adapter 統一 | HIGH | 5分 |
| B | pipeline.execute() 整理 | HIGH | 15分 |
| C | EasyModeWorkflow テスト | HIGH | 30分 |
| D | FullAutoWorkflow テスト | HIGH | 30分 |
| E | 全テスト実行 | HIGH | 10分 |
| F | ruff チェック | MEDIUM | 15分 |
| G | mypy 修正 | MEDIUM | 20分 |
| H | USE_UNIFIED フラグ整理 | MEDIUM | 10分 |
| I | ドキュメント更新 | MEDIUM | 30分 |
| J | 旧計画 DEPRECATED 化 | LOW | 5分 |
| **合計** | | | **約 2.5時間** |

---

## リスク評価

### HIGH リスク
- **Step B**: `pipeline.execute()` 変更が既存 26 テストに波及する可能性
  - 緩和策: 既存テストは reporter パラメータをモックで渡しているため、Adapter 再 wrap を消しても動作するはず
- **Step H-1**: フラグ削除により、外部スクリプトが `USE_UNIFIED_PIPELINE=0` を指定していると影響
  - 緩和策: 削除前に `grep` で参照箇所確認

### MEDIUM リスク
- **Step C/D**: モックのセットアップが複雑で import エラーが発生する可能性
  - 緩和策: 既存の `tests/test_unified_pipeline.py` の `MockEngine` を参考に

### LOW リスク
- ドキュメント更新 (Step I, J) はテキスト編集のみ

---

## 成功基準 (Definition of Done)

- [ ] `EasyModeWorkflow` が `ProgressReporterAdapter` を使用
- [ ] `pipeline.execute()` の重複 wrap が解消
- [ ] `tests/test_easy_mode_workflow.py` 追加、全テスト pass
- [ ] `tests/test_full_auto_workflow.py` 追加、全テスト pass
- [ ] 全テストスイート 0 failures
- [ ] `ruff check src/` で新規エラー 0
- [ ] 4 つのドキュメント更新完了
- [ ] 旧 3 計画書が DEPRECATED 化

---

## 参考情報

### 既存ファイル
- 委譲先: `src/services/auto_workflow_pipeline.py` (203行)
- 委譲元: `src/backend/workflows/{full,easy_mode}_workflow.py` (各 ~80行)
- マッパー: `src/services/pipeline_param_mapper.py` (116行)
- Adapter: `src/services/progress_reporter.py` (172行)
- テスト: `tests/test_unified_pipeline.py` (783行、26テスト pass)

### 削除済み
- `src/easy_mode/pipeline.py` (旧 EasyModePipeline 実装)

### 関連 ADR / 設計書
- `PIPELINE_UNIFICATION_PLAN.md`
- `UNIFIED_PIPELINE_IMPLEMENTATION_PLAN.md`
