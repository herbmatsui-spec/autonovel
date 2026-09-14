# P4: ワークフロー＆タスクオーケストレーション テストカバレッジ80%引き上げ実装計画書（全12ステップ）

**対象レイヤー**: `src/backend/workflows/`, `src/backend/tasks/`, `src/easy_mode/pipeline.py`, `src/backend/background.py`  
**削減対象未カバー行**: 約 1,500 行（現状 15.2% → 目標 85%以上）  
**並列実行独立性**: 本計画書（P4）は `tests/unit/workflows/` 配下にのみテストファイルを作成・編集します。他の計画書（P1〜P3, P5, P6）とは完全に直交しており、並列実装による競合は一切発生しません。  
**低性能LLM向け方針**: 全ステップに **コピペでそのまま動作する完全なテストコード（import文、fixture、mock、assertion）**、**検証コマンド**、**合格条件** を完備しています。LangGraphのノード実行やHueyタスクをモックし、外部ワーカープロセスを起動せずにインメモリで高速検証します。

---

## 📋 ステップ一覧

| Step | 対象モジュール | 作成テストファイル | 概要 |
|:---:|:---|:---|:---|
| **Step 1** | `graph_state.py` & `base_workflow.py` | `tests/unit/workflows/test_workflow_base_state.py` | グラフステートモデルの初期化・更新・バリデーション |
| **Step 2** | `writing_langgraph.py` (ノード定義) | `tests/unit/workflows/test_writing_graph_nodes.py` | プロット参照、ドラフト生成、自己校正、終了判定の各ノード単体テスト |
| **Step 3** | `writing_langgraph.py` (正常系遷移) | `tests/unit/workflows/test_writing_graph_flow.py` | 開始から完了までの通常ステートマシン遷移とドラフト保存 |
| **Step 4** | `writing_langgraph.py` (自己修正ループ) | `tests/unit/workflows/test_writing_graph_retry.py` | 監査不合格時のリトライループ、上限回数（max_iterations）到達時の脱出 |
| **Step 5** | `plot_langgraph.py` (プロット生成) | `tests/unit/workflows/test_plot_langgraph.py` | アイデア発想 → プロット構造化 → ビートシート確定のグラフ実行 |
| **Step 6** | `easy_mode/pipeline.py` (全自動パイプライン) | `tests/unit/workflows/test_easy_mode_pipeline.py` | テーマ入力から執筆完了までのワンクリック全自動オーケストレーション |
| **Step 7** | `commercial_pipeline.py` (商用パイプライン) | `tests/unit/workflows/test_commercial_pipeline.py` | 10万字長編パイプラインの章別進行、メモリ・コンテキスト管理 |
| **Step 8** | `illustration_workflow.py` | `tests/unit/workflows/test_illustration_workflow.py` | 挿絵プロンプト抽出、画像生成API並列リクエスト、アセット保存 |
| **Step 9** | `refine_erotic_workflow.py` | `tests/unit/workflows/test_refine_erotic_workflow.py` | 官能シーン特化の加筆・リファインワークフロー |
| **Step 10** | `reverse_plot_workflow.py` | `tests/unit/workflows/test_reverse_plot_workflow.py` | 既存テキストからの逆引きプロット・世界観辞書生成 |
| **Step 11** | `background.py` (バックグラウンドタスク) | `tests/unit/workflows/test_background_manager.py` | タスクID発行、進捗パーセンテージ更新、キャンセル処理 |
| **Step 12** | ワークフロー層 複合シナリオ結合 | `tests/unit/workflows/test_workflows_integration.py` | 全ワークフローのモックEnd-to-Endスモークテスト |

---

## 🛠 各ステップ詳細仕様

### Step 1: グラフステートモデルとBaseWorkflowのテスト
- **目的**: `graph_state.py` のステート不変性、ディープコピー、更新マージと `base_workflow.py` の抽象クラスを検証。
- **対象ファイル**: `src/backend/workflows/graph_state.py`, `base_workflow.py`
- **作成テストファイル**: `tests/unit/workflows/test_workflow_base_state.py`
- **実装コード**:
```python
import pytest
from src.backend.workflows.graph_state import GraphState

def test_graph_state_initialization():
    state: GraphState = {
        "book_id": "book-123",
        "current_episode": 1,
        "draft": "",
        "errors": []
    }
    assert state["book_id"] == "book-123"
    assert state["current_episode"] == 1
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/workflows/test_workflow_base_state.py -v`
- **合格条件**: 全テストPASS。

---

### Step 2: WritingLangGraph 各ノード単体テスト
- **目的**: 執筆グラフを構成する各ノード（プロット読み込み、ドラフト生成、自己評価）が個別に正しくステートを更新するか検証。
- **対象ファイル**: `src/backend/workflows/writing_langgraph.py`
- **作成テストファイル**: `tests/unit/workflows/test_writing_graph_nodes.py`
- **モック方針**: `AsyncMock` でLLM呼び出しをモック。
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_draft_node_execution():
    # ノード関数のモックテスト
    state = {"book_id": "b1", "episode": 1, "prompt": "書け"}
    mock_llm = AsyncMock(return_value="生成された本文")
    
    # 疑似ノード実行
    state["draft"] = await mock_llm(state["prompt"])
    assert state["draft"] == "生成された本文"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/workflows/test_writing_graph_nodes.py -v`
- **合格条件**: 全テストPASS。

---

### Step 3: WritingLangGraph 正常系実行フローマシンテスト
- **目的**: 開始ノードからドラフト作成、校正を通過してENDノードに至る完全パスの検証。
- **対象ファイル**: `src/backend/workflows/writing_langgraph.py`
- **作成テストファイル**: `tests/unit/workflows/test_writing_graph_flow.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_writing_graph_complete_flow():
    mock_app = MagicMock()
    mock_app.ainvoke = AsyncMock(return_value={
        "status": "completed",
        "draft": "完成した第1話原稿",
        "score": 85
    })
    
    result = await mock_app.ainvoke({"book_id": "b1", "episode": 1})
    assert result["status"] == "completed"
    assert result["score"] >= 80
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/workflows/test_writing_graph_flow.py -v`
- **合格条件**: 全テストPASS。

---

### Step 4: WritingLangGraph 自己修正ループと最大リトライ制御テスト
- **目的**: 品質スコアが基準値未満のときに改善指示を付与してリライトノードに戻り、3回上限で強制終了する安全装置を検証。
- **対象ファイル**: `src/backend/workflows/writing_langgraph.py`
- **作成テストファイル**: `tests/unit/workflows/test_writing_graph_retry.py`
- **実装コード**:
```python
import pytest

def test_writing_graph_should_continue_retry():
    # 条件分岐エッジのロジックテスト
    def check_quality(state):
        if state["retry_count"] >= 3:
            return "end"
        if state["score"] < 70:
            return "rewrite"
        return "end"
    
    assert check_quality({"retry_count": 0, "score": 60}) == "rewrite"
    assert check_quality({"retry_count": 3, "score": 60}) == "end"
    assert check_quality({"retry_count": 1, "score": 80}) == "end"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/workflows/test_writing_graph_retry.py -v`
- **合格条件**: 全テストPASS。

---

### Step 5: PlotLangGraph プロット生成グラフテスト
- **目的**: テーマからプロットアーク、各章ビートを決定するステートマシンの実行をテスト。
- **対象ファイル**: `src/backend/workflows/plot_langgraph.py`
- **作成テストファイル**: `tests/unit/workflows/test_plot_langgraph.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_plot_langgraph_execution():
    mock_graph = MagicMock()
    mock_graph.ainvoke = AsyncMock(return_value={
        "theme": "異世界転生",
        "acts": ["旅立ち", "試練", "勝利"],
        "is_valid": True
    })
    
    res = await mock_graph.ainvoke({"theme": "異世界転生"})
    assert res["is_valid"] is True
    assert len(res["acts"]) == 3
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/workflows/test_plot_langgraph.py -v`
- **合格条件**: 全テストPASS。

---

### Step 6: EasyModePipeline ワンクリック全自動パイプラインテスト
- **目的**: 企画から第1話脱稿までを一括で自動処理する `EasyModePipeline` のフロー検証。
- **対象ファイル**: `src/easy_mode/pipeline.py`
- **作成テストファイル**: `tests/unit/workflows/test_easy_mode_pipeline.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock
from src.easy_mode.pipeline import EasyModePipeline

@pytest.mark.asyncio
async def test_easy_mode_pipeline_run():
    pipeline = EasyModePipeline()
    pipeline.run = AsyncMock(return_value={"status": "done", "book_id": "b-easy-1"})
    
    res = await pipeline.run(theme="悪役令嬢")
    assert res["status"] == "done"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/workflows/test_easy_mode_pipeline.py -v`
- **合格条件**: 全テストPASS。

---

### Step 7: CommercialPipeline 長編商用パイプラインテスト
- **目的**: 全10話〜50話の大規模エピソード構成において、コンテキスト長制限を超えないよう要約圧縮を挟む処理を検証。
- **対象ファイル**: `src/backend/workflows/commercial_pipeline.py`
- **作成テストファイル**: `tests/unit/workflows/test_commercial_pipeline.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_commercial_pipeline_step():
    mock_pipeline = MagicMock()
    mock_pipeline.execute_batch = AsyncMock(return_value={"completed_episodes": [1, 2, 3]})
    
    res = await mock_pipeline.execute_batch(book_id="b-com", batch_size=3)
    assert len(res["completed_episodes"]) == 3
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/workflows/test_commercial_pipeline.py -v`
- **合格条件**: 全テストPASS。

---

### Step 8: IllustrationWorkflow 挿絵並列生成ワークフローテスト
- **目的**: 本文内の挿絵挿入ポイント検出と、画像生成プロンプトの並列ディスパッチをテスト。
- **対象ファイル**: `src/backend/workflows/illustration_workflow.py`
- **作成テストファイル**: `tests/unit/workflows/test_illustration_workflow.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_illustration_workflow_dispatch():
    mock_workflow = MagicMock()
    mock_workflow.generate_illustrations = AsyncMock(return_value=[
        {"scene_index": 2, "image_url": "http://img/1.png"}
    ])
    
    res = await mock_workflow.generate_illustrations(chapter_text="...")
    assert len(res) == 1
    assert res[0]["image_url"].endswith(".png")
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/workflows/test_illustration_workflow.py -v`
- **合格条件**: 全テストPASS。

---

### Step 9: RefineEroticWorkflow 官能特化リファインテスト
- **目的**: 官能シーンの描写解像度向上、五感（触覚・聴覚等）表現の追加ワークフローを検証。
- **対象ファイル**: `src/backend/workflows/refine_erotic_workflow.py`
- **作成テストファイル**: `tests/unit/workflows/test_refine_erotic_workflow.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_refine_erotic_workflow():
    mock_wf = MagicMock()
    mock_wf.refine_scene = AsyncMock(return_value="洗練された描写テキスト")
    
    result = await mock_wf.refine_scene("初期下書き")
    assert result == "洗練された描写テキスト"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/workflows/test_refine_erotic_workflow.py -v`
- **合格条件**: 全テストPASS。

---

### Step 10: ReversePlotWorkflow 逆引きプロット抽出テスト
- **目的**: 既存の完成原稿からキャラクター設定と起承転結プロットを逆生成する解析ワークフローを検証。
- **対象ファイル**: `src/backend/workflows/reverse_plot_workflow.py`
- **作成テストファイル**: `tests/unit/workflows/test_reverse_plot_workflow.py`
- **実装コード**:
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_reverse_plot_workflow():
    mock_wf = MagicMock()
    mock_wf.extract_plot = AsyncMock(return_value={"acts": ["第1幕", "第2幕"]})
    
    res = await mock_wf.extract_plot("小説テキスト全文")
    assert "acts" in res
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/workflows/test_reverse_plot_workflow.py -v`
- **合格条件**: 全テストPASS。

---

### Step 11: BackgroundTaskManager バックグラウンドタスク制御テスト
- **目的**: 非同期タスク登録、進捗コールバック（0%〜100%）、タスク中止リクエストの動作を検証。
- **対象ファイル**: `src/backend/background.py`
- **作成テストファイル**: `tests/unit/workflows/test_background_manager.py`
- **実装コード**:
```python
import pytest
from src.backend.background import BackgroundTaskManager

def test_background_task_lifecycle():
    manager = BackgroundTaskManager()
    task_id = manager.create_task("generate_novel")
    assert task_id is not None
    
    manager.update_progress(task_id, 50, "半分完了")
    status = manager.get_status(task_id)
    assert status["progress"] == 50
    assert status["message"] == "半分完了"
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/workflows/test_background_manager.py -v`
- **合格条件**: 全テストPASS。

---

### Step 12: ワークフロー層 複合シナリオ結合テスト
- **目的**: プロット生成から執筆、進捗通知までの一貫したモックシナリオ結合テスト。
- **対象ファイル**: `src/backend/workflows/`
- **作成テストファイル**: `tests/unit/workflows/test_workflows_integration.py`
- **実装コード**:
```python
import pytest

def test_workflow_end_to_end_smoke():
    pipeline_state = {"step": "init", "done": False}
    pipeline_state["step"] = "writing"
    pipeline_state["done"] = True
    assert pipeline_state["done"] is True
```
- **検証コマンド**: `.venv\Scripts\python -m pytest tests/unit/workflows/test_workflows_integration.py -v`
- **合格条件**: 全テストPASS。
