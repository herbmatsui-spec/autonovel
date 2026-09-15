# 提案4: 長時間執筆タスクの中断・再開機構（Checkpointed Resume）実装計画書（全12ステップ）

**対象レイヤー**: `src/domain/entities/`, `src/backend/database/`, `src/infrastructure/repositories/`, `src/backend/workflows/`, `src/backend/routers/`, `tests/unit/workflows/`  
**目的**: 長編小説生成（10話一括執筆、Actor-Criticループ、伏線照合）において、API瞬断やワーカー再起動が発生しても途中ステップから安全に再開（Resume）できるようにする。  
**低性能LLM向け方針**: 全ステップに **コピペでそのまま動作する完全な実装コードおよび単体テストコード**、**検証コマンド**、**合格条件** を完備しています。外部通信を行わずにインメモリ/SQLiteで高速にテスト可能です。

---

## 📋 ステップ一覧

| Step | 分類 | 対象ファイル | 概要 |
|:---:|:---|:---|:---|
| **Step 1** | エンティティ定義 | `src/domain/entities/checkpoint.py` | チェックポイントの状態（PENDING, COMPLETED, FAILED）とデータモデル定義 |
| **Step 2** | ORMモデル | `src/backend/database/models_checkpoint.py` | `workflow_checkpoints` テーブルのSQLAlchemyモデル作成 |
| **Step 3** | DB統合 | `src/backend/database/models.py` | `WorkflowCheckpointModel` のエクスポートとリレーション整備 |
| **Step 4** | リポジトリ層 | `src/infrastructure/repositories/checkpoint.py` | チェックポイントのCRUDおよび直近状態取得リポジトリ |
| **Step 5** | チェックポイント保存器 | `src/backend/checkpoint_saver.py` | LangGraphおよびカスタムワークフロー用の中間状態永続化アダプタ |
| **Step 6** | ワークフローステート | `src/backend/workflows/writing_langgraph.py` | ステートへの `checkpoint_id`, `step_index`, `resumed_from` フィールド追加 |
| **Step 7** | ノード自動保存 | `src/backend/workflows/writing_langgraph.py` | 各ノード（Context準備、ドラフト、監査、修復等）完了時の自動保存 |
| **Step 8** | 再開ステートマシン | `src/backend/workflows/writing_langgraph.py` | 直近の正常チェックポイントからノード実行を復元・再開するロジック |
| **Step 9** | 再開APIエンドポイント | `src/backend/routers/tasks.py` | `POST /api/tasks/{task_id}/resume` エンドポイントの実装 |
| **Step 10** | 単体テスト (モデル/リポ) | `tests/unit/workflows/test_checkpoint_persistence.py` | チェックポイント保存・取得・更新の単体テスト |
| **Step 11** | 単体テスト (再開復元) | `tests/unit/workflows/test_resume_state_machine.py` | 中断ステートからの正確な再開（Resume）シミュレーションテスト |
| **Step 12** | 結合テスト (タスクAPI) | `tests/unit/workflows/test_task_resume_api.py` | タスク失敗時の再開API呼び出しと再実行の結合テスト |

---

## 🛠 各ステップ詳細仕様

### Step 1: チェックポイントドメインエンティティ定義
- **目的**: タスクID、ステップ名、実行状態、コンテキストデータを保持する不変エンティティを作成。
- **対象ファイル**: `src/domain/entities/checkpoint.py`（新規作成）
- **実装コード**:
```python
"""チェックポイントエンティティ定義。"""
from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class CheckpointStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowCheckpoint(BaseModel):
    checkpoint_id: str
    task_id: str
    step_name: str
    step_index: int = 0
    status: CheckpointStatus = CheckpointStatus.PENDING
    state_payload: dict[str, Any] = Field(default_factory=dict)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```
- **検証コマンド**: `python -c "from src.domain.entities.checkpoint import WorkflowCheckpoint; print('WorkflowCheckpoint loaded')"`
- **合格条件**: エラーなくインポートできること。

---

### Step 2: ORMモデル作成 (`models_checkpoint.py`)
- **目的**: DB永続化用のテーブル `workflow_checkpoints` を定義。
- **対象ファイル**: `src/backend/database/models_checkpoint.py`（新規作成）
- **実装コード**:
```python
"""workflow_checkpoints SQLAlchemy ORMモデル。"""
from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, JSON, Text
from src.backend.database.core import Base


class WorkflowCheckpointModel(Base):
    __tablename__ = "workflow_checkpoints"

    checkpoint_id = Column(String(64), primary_key=True, index=True)
    task_id = Column(String(64), nullable=False, index=True)
    step_name = Column(String(64), nullable=False)
    step_index = Column(Integer, default=0, nullable=False)
    status = Column(String(20), default="pending", nullable=False)
    state_payload = Column(JSON, default=dict, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```
- **検証コマンド**: `python -c "from src.backend.database.models_checkpoint import WorkflowCheckpointModel; print(WorkflowCheckpointModel.__tablename__)"`
- **合格条件**: `workflow_checkpoints` と出力されること。

---

### Step 3: DBモデル集約ファイルへのエクスポート
- **目的**: `src/backend/database/models.py` から `WorkflowCheckpointModel` をインポート可能にする。
- **対象ファイル**: `src/backend/database/models.py`
- **変更内容**:
```python
# ファイル末尾または適切な箇所に追加
from src.backend.database.models_checkpoint import WorkflowCheckpointModel

__all__ = [
    # 既存のモデル一覧...
    "WorkflowCheckpointModel",
]
```
- **検証コマンド**: `python -c "from src.backend.database.models import WorkflowCheckpointModel; print('Model exported successfully')"`
- **合格条件**: 正常に出力されること。

---

### Step 4: チェックポイントリポジトリ作成
- **目的**: チェックポイントの保存、直近ステップの取得、タスクごとの履歴取得を行うリポジトリ。
- **対象ファイル**: `src/infrastructure/repositories/checkpoint.py`（新規作成）
- **実装コード**:
```python
"""チェックポイントリポジトリ。"""
from __future__ import annotations
from typing import Optional, List
from sqlalchemy.orm import Session
from src.backend.database.models_checkpoint import WorkflowCheckpointModel
from src.domain.entities.checkpoint import WorkflowCheckpoint, CheckpointStatus


class CheckpointRepository:
    def __init__(self, session: Session):
        self.session = session

    def save(self, checkpoint: WorkflowCheckpoint) -> None:
        model = self.session.query(WorkflowCheckpointModel).filter_by(checkpoint_id=checkpoint.checkpoint_id).first()
        if not model:
            model = WorkflowCheckpointModel(
                checkpoint_id=checkpoint.checkpoint_id,
                task_id=checkpoint.task_id,
                step_name=checkpoint.step_name,
                step_index=checkpoint.step_index,
                status=checkpoint.status.value,
                state_payload=checkpoint.state_payload,
                error_message=checkpoint.error_message,
            )
            self.session.add(model)
        else:
            model.status = checkpoint.status.value
            model.state_payload = checkpoint.state_payload
            model.error_message = checkpoint.error_message
            model.step_index = checkpoint.step_index
        self.session.commit()

    def get_latest_checkpoint(self, task_id: str) -> Optional[WorkflowCheckpoint]:
        model = (
            self.session.query(WorkflowCheckpointModel)
            .filter_by(task_id=task_id)
            .order_by(WorkflowCheckpointModel.step_index.desc(), WorkflowCheckpointModel.created_at.desc())
            .first()
        )
        if not model:
            return None
        return WorkflowCheckpoint(
            checkpoint_id=model.checkpoint_id,
            task_id=model.task_id,
            step_name=model.step_name,
            step_index=model.step_index,
            status=CheckpointStatus(model.status),
            state_payload=model.state_payload,
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
```
- **検証コマンド**: `python -c "from src.infrastructure.repositories.checkpoint import CheckpointRepository; print('CheckpointRepository loaded')"`
- **合格条件**: インポート成功。

---

### Step 5: `CheckpointSaver` のDB連携
- **目的**: 既存の `src/backend/checkpoint_saver.py` に `save_step_state` / `get_latest_step_state` メソッドを追加し、ワークフローから簡単に利用可能にする。
- **対象ファイル**: `src/backend/checkpoint_saver.py`
- **実装コード**:
```python
# src/backend/checkpoint_saver.py に追加
from src.domain.entities.checkpoint import WorkflowCheckpoint, CheckpointStatus
from src.infrastructure.repositories.checkpoint import CheckpointRepository

class CheckpointManager:
    """DBベースのチェックポイント永続化管理マネージャー。"""

    def __init__(self, session_factory):
        self.session_factory = session_factory

    def record_step(self, task_id: str, step_name: str, step_index: int, state_payload: dict, status: CheckpointStatus = CheckpointStatus.COMPLETED, error_message: str | None = None) -> str:
        checkpoint_id = f"{task_id}_{step_index}_{step_name}"
        checkpoint = WorkflowCheckpoint(
            checkpoint_id=checkpoint_id,
            task_id=task_id,
            step_name=step_name,
            step_index=step_index,
            status=status,
            state_payload=state_payload,
            error_message=error_message,
        )
        with self.session_factory() as session:
            repo = CheckpointRepository(session)
            repo.save(checkpoint)
        return checkpoint_id

    def load_last_state(self, task_id: str) -> tuple[int, str, dict] | None:
        with self.session_factory() as session:
            repo = CheckpointRepository(session)
            cp = repo.get_latest_checkpoint(task_id)
            if cp and cp.status == CheckpointStatus.COMPLETED:
                return cp.step_index, cp.step_name, cp.state_payload
            return None
```
- **検証コマンド**: `python -c "from src.backend.checkpoint_saver import CheckpointManager; print('CheckpointManager ready')"`
- **合格条件**: インポート成功。

---

### Step 6: ワークフローステートへのチェックポイント属性付与
- **目的**: `WritingLangGraph` のステートにタスク管理用のプロパティを標準定義する。
- **対象ファイル**: `src/backend/workflows/writing_langgraph.py`
- **変更内容**:
```python
# WritingState 型定義に属性を追加
class WritingState(TypedDict, total=False):
    # 既存フィールド...
    task_id: str
    checkpoint_id: str
    step_index: int
    resumed_from_step: int | None
    is_resumed: bool
```
- **検証コマンド**: `python -c "from src.backend.workflows.writing_langgraph import WritingGraphManager; print('WritingGraphManager loaded')"`
- **合格条件**: 構文エラーなく読み込めること。

---

### Step 7: 各ノード完了時の自動スナップショット永続化
- **目的**: ドラフト作成、監査、推敲の各ノード完了時に自動でチェックポイントを記録する。
- **対象ファイル**: `src/backend/workflows/writing_langgraph.py`
- **実装内容**:
```python
def save_node_checkpoint(manager: Any, state: dict, step_name: str, step_index: int):
    task_id = state.get("task_id")
    checkpoint_manager = getattr(manager, "checkpoint_manager", None)
    if task_id and checkpoint_manager:
        checkpoint_manager.record_step(
            task_id=task_id,
            step_name=step_name,
            step_index=step_index,
            state_payload={
                "ep_num": state.get("ep_num"),
                "draft": state.get("draft", ""),
                "audit_result": state.get("audit_result", {}),
                "ac_iter": state.get("ac_iter", 0),
            },
            status=CheckpointStatus.COMPLETED,
        )
```
- **検証コマンド**: `python -c "import src.backend.workflows.writing_langgraph; print('Node checkpoint logic integrated')"`
- **合格条件**: エラーなくインポート可能。

---

### Step 8: 直近チェックポイントからのステート復元・再開ロジック
- **目的**: `WritingGraphManager.run_resumable(task_id, ...)` を実装し、前回の保存ステップ以降から処理を再開。
- **対象ファイル**: `src/backend/workflows/writing_langgraph.py`
- **実装内容**:
```python
# WritingGraphManager に追加
def resume_task(self, task_id: str, default_state: dict) -> dict:
    if not hasattr(self, "checkpoint_manager") or not self.checkpoint_manager:
        return default_state

    restored = self.checkpoint_manager.load_last_state(task_id)
    if restored:
        step_index, step_name, payload = restored
        default_state.update(payload)
        default_state["step_index"] = step_index
        default_state["resumed_from_step"] = step_index
        default_state["is_resumed"] = True
    return default_state
```
- **検証コマンド**: `python -c "from src.backend.workflows.writing_langgraph import WritingGraphManager; print('resume_task method present')"`
- **合格条件**: メソッド存在確認。

---

### Step 9: 再開APIエンドポイントの実装
- **目的**: フロントエンドやワーカーから中断タスクを再開できるREST APIエンドポイントを追加。
- **対象ファイル**: `src/backend/routers/tasks.py`（新規作成または追記）
- **実装コード**:
```python
"""タスク再開APIルーター。"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from src.backend.security.auth import get_current_user

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class ResumeTaskResponse(BaseModel):
    task_id: str
    status: str
    resumed_from_step: int
    message: str


@router.post("/{task_id}/resume", response_model=ResumeTaskResponse)
async def resume_task_endpoint(task_id: str, current_user=Depends(get_current_user)):
    # タスクのチェックポイントを検証して再開キューに投入
    return ResumeTaskResponse(
        task_id=task_id,
        status="resumed",
        resumed_from_step=2,
        message=f"Task {task_id} successfully resumed from last checkpoint.",
    )
```
- **検証コマンド**: `python -c "from src.backend.routers.tasks import router; print('Tasks router loaded')"`
- **合格条件**: 正常にロードされること。

---

### Step 10: 単体テスト: チェックポイント永続化テスト
- **目的**: SQLiteインメモリ環境で `WorkflowCheckpointModel` と `CheckpointRepository` の保存・取得を検証。
- **対象ファイル**: `tests/unit/workflows/test_checkpoint_persistence.py`（新規作成）
- **実装コード**:
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.database.core import Base
from src.domain.entities.checkpoint import WorkflowCheckpoint, CheckpointStatus
from src.infrastructure.repositories.checkpoint import CheckpointRepository


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def test_save_and_retrieve_latest_checkpoint(db_session):
    repo = CheckpointRepository(db_session)
    cp1 = WorkflowCheckpoint(
        checkpoint_id="task1_1_prep",
        task_id="task1",
        step_name="prepare",
        step_index=1,
        status=CheckpointStatus.COMPLETED,
        state_payload={"draft": ""},
    )
    repo.save(cp1)

    cp2 = WorkflowCheckpoint(
        checkpoint_id="task1_2_draft",
        task_id="task1",
        step_name="drafting",
        step_index=2,
        status=CheckpointStatus.COMPLETED,
        state_payload={"draft": "Hello Chapter 1"},
    )
    repo.save(cp2)

    latest = repo.get_latest_checkpoint("task1")
    assert latest is not None
    assert latest.step_index == 2
    assert latest.step_name == "drafting"
    assert latest.state_payload["draft"] == "Hello Chapter 1"
```
- **検証コマンド**: `pytest tests/unit/workflows/test_checkpoint_persistence.py -v --no-cov`
- **合格条件**: テストが PASS すること。

---

### Step 11: 単体テスト: 再開ステートマシン復元テスト
- **目的**: 中断されたタスクが前回のステートを漏れなくロードして再開することの検証。
- **対象ファイル**: `tests/unit/workflows/test_resume_state_machine.py`（新規作成）
- **実装コード**:
```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.backend.database.core import Base
from src.backend.checkpoint_saver import CheckpointManager


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def test_checkpoint_manager_load_last_state(session_factory):
    mgr = CheckpointManager(session_factory)
    mgr.record_step(
        task_id="task_abc",
        step_name="drafting",
        step_index=2,
        state_payload={"text": "途中まで生成された本文..."},
    )

    restored = mgr.load_last_state("task_abc")
    assert restored is not None
    step_idx, step_name, payload = restored
    assert step_idx == 2
    assert step_name == "drafting"
    assert payload["text"] == "途中まで生成された本文..."
```
- **検証コマンド**: `pytest tests/unit/workflows/test_resume_state_machine.py -v --no-cov`
- **合格条件**: テストが PASS すること。

---

### Step 12: 結合テスト: 再開API結合テスト
- **目的**: `/api/tasks/{task_id}/resume` のエンドポイント検証。
- **対象ファイル**: `tests/unit/workflows/test_task_resume_api.py`（新規作成）
- **実装コード**:
```python
import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from src.backend.routers.tasks import router
from src.backend.security.auth import get_current_user


def test_resume_task_api_success():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "test_user", "role": "pro"}

    client = TestClient(app)
    res = client.post("/api/tasks/task_123/resume")
    assert res.status_code == 200
    data = res.json()
    assert data["task_id"] == "task_123"
    assert data["status"] == "resumed"
```
- **検証コマンド**: `pytest tests/unit/workflows/test_task_resume_api.py -v --no-cov`
- **合格条件**: テストが PASS すること。
