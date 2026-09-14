import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.backend.workflows.plot_langgraph import PlotGraphManager


@pytest.mark.asyncio
async def test_plot_langgraph_fallback_execution():
    """langgraphが利用できない場合のフォールバックパスをテスト"""
    # モックエンジンを作成
    mock_engine = MagicMock()
    mock_engine.repo = MagicMock()
    mock_engine.repo.create_or_replace_plot = AsyncMock()
    mock_engine.pm = MagicMock()
    mock_engine.ctx_mgr = MagicMock()
    mock_engine.ctx_mgr.get_optimal_context = AsyncMock(return_value=(
        {"character_id": 1, "traits": ["brave"]},  # character_context
        {"prev_events": ["event1"]}                 # previous_context
    ))
    mock_engine.generate_json = AsyncMock()
    mock_engine.generate_json.return_value = MagicMock(
        success=True,
        metadata={"scenes": [{"title": "Scene 1", "content": "content"}]}
    )
    mock_engine.logic_validator = MagicMock()
    mock_engine.auditor = MagicMock()
    mock_engine.auditor.audit = AsyncMock(return_value=MagicMock(model_dump=lambda: {"consistent": True}))
    mock_engine.narrative = MagicMock()
    
    # PlotGraphManagerのインスタンスを作成
    manager = PlotGraphManager(mock_engine)
    
    # langgraphが利用できない場合のフォールバックパスをテストするため、
    # あえてHAS_LANGGRAPHをFalseにする
    with patch('src.backend.workflows.plot_langgraph.HAS_LANGGRAPH', False):
        # runメソッドを実行
        result = await manager.run(book_id=1, ep_num=1, branch_id=1)
        
        # アサーション
        assert result["status"] == "completed"
        assert "final_plot" in result
        assert result["final_plot"]["book_id"] == 1
        assert result["final_plot"]["ep_num"] == 1
        assert result["final_plot"]["branch_id"] == 1
        assert "blueprint" in result["final_plot"]
        assert "scenes" in result["final_plot"]
        
        # 各フェーズが呼ばれたことを確認
        mock_engine.ctx_mgr.get_optimal_context.assert_called_once_with(1, 1, 1)
        mock_engine.generate_json.assert_called_once()
        mock_engine.auditor.audit.assert_called_once()
        mock_engine.repo.create_or_replace_plot.assert_called_once()


@pytest.mark.asyncio
async def test_plot_langgraph_with_mocked_workflow():
    """モックしたワークフローでフローをテスト"""
    # モックエンジンを作成
    mock_engine = MagicMock()
    mock_engine.repo = MagicMock()
    mock_engine.pm = MagicMock()
    mock_engine.ctx_mgr = MagicMock()
    mock_engine.generate_json = MagicMock()
    mock_engine.logic_validator = MagicMock()
    mock_engine.auditor = MagicMock()
    mock_engine.narrative = MagicMock()
    
    # PlotGraphManagerのインスタンスを作成
    manager = PlotGraphManager(mock_engine)
    
    # langgraphが利用可能な状態をシミュレート
    # workflow属性にモックを直接設定
    mock_workflow = MagicMock()
    mock_workflow.ainvoke = AsyncMock(return_value={
        "book_id": 1,
        "ep_num": 1,
        "branch_id": 1,
        "status": "completed",
        "final_plot": {
            "book_id": 1,
            "ep_num": 1,
            "branch_id": 1,
            "blueprint": {"scenes": [{"title": "Test Scene"}]},
            "scenes": [{"title": "Test Scene", "content": "test content"}]
        }
    })
    manager.workflow = mock_workflow
    
    # runメソッドを実行
    result = await manager.run(book_id=1, ep_num=1, branch_id=1)
    
    # アサーション（計画書の例に合わせる）
    assert result["status"] == "completed"
    assert "final_plot" in result
    assert result["final_plot"]["book_id"] == 1
    assert result["final_plot"]["ep_num"] == 1
    assert "scenes" in result["final_plot"]
    assert len(result["final_plot"]["scenes"]) >= 1
    
    # ainvokeが呼ばれたことを確認
    mock_workflow.ainvoke.assert_called_once()
    
    # 渡された初期状態を確認
    call_args = mock_workflow.ainvoke.call_args[0][0]
    assert call_args["book_id"] == 1
    assert call_args["ep_num"] == 1
    assert call_args["branch_id"] == 1
    assert call_args["status"] == "starting"


def test_plot_graph_manager_initialization():
    """PlotGraphManagerの初期化をテスト"""
    mock_engine = MagicMock()
    mock_engine.repo = MagicMock()
    mock_engine.pm = MagicMock()
    mock_engine.ctx_mgr = MagicMock()
    mock_engine.generate_json = MagicMock()
    mock_engine.logic_validator = MagicMock()
    mock_engine.auditor = MagicMock()
    mock_engine.narrative = MagicMock()
    
    manager = PlotGraphManager(mock_engine)
    
    assert manager.engine == mock_engine
    assert manager.repo == mock_engine.repo
    assert manager.pm == mock_engine.pm
    assert manager.ctx_mgr == mock_engine.ctx_mgr
    assert manager.generate_json == mock_engine.generate_json
    assert manager.logic_validator == mock_engine.logic_validator
    assert manager.auditor == mock_engine.auditor
    assert manager.narrative == mock_engine.narrative


@pytest.mark.asyncio
async def test_node_align_context():
    """node_align_contextのテスト"""
    mock_engine = MagicMock()
    mock_engine.ctx_mgr = MagicMock()
    mock_engine.ctx_mgr.get_optimal_context = AsyncMock(return_value=(
        {"character_id": 1, "traits": ["brave"]},
        {"prev_events": ["event1"]}
    ))
    
    manager = PlotGraphManager(mock_engine)
    
    state = {
        "book_id": 1,
        "ep_num": 1,
        "branch_id": 1
    }
    
    result = await manager.node_align_context(state)
    
    assert result["context_alignment"]["character_context"] == {"character_id": 1, "traits": ["brave"]}
    assert result["context_alignment"]["previous_context"] == {"prev_events": ["event1"]}
    assert result["status"] == "context_aligned"


@pytest.mark.asyncio
async def test_node_generate_blueprint():
    """node_generate_blueprintのテスト"""
    mock_engine = MagicMock()
    mock_engine.generate_json = AsyncMock()
    mock_engine.generate_json.return_value = MagicMock(
        success=True,
        metadata={"plot_points": ["point1", "point2"]}
    )
    
    manager = PlotGraphManager(mock_engine)
    
    state = {
        "book_id": 1,
        "ep_num": 1
    }
    
    result = await manager.node_generate_blueprint(state)
    
    assert result["blueprint"] == {"plot_points": ["point1", "point2"]}
    assert result["status"] == "blueprint_generated"
    
    # プロンプトが正しく生成されたことを確認
    mock_engine.generate_json.assert_called_once()
    call_args = mock_engine.generate_json.call_args
    assert call_args[0][0] == "gemini-3.1-flash-lite"  # モデル名
    assert "Generate plot blueprint for book 1, ep 1" in call_args[0][1]  # プロンプト


@pytest.mark.asyncio
async def test_node_audit_plot():
    """node_audit_plotのテスト"""
    mock_engine = MagicMock()
    mock_engine.auditor = MagicMock()
    mock_engine.auditor.audit = AsyncMock(return_value=MagicMock(
        model_dump=lambda: {"consistent": True, "score": 0.9}
    ))
    
    manager = PlotGraphManager(mock_engine)
    
    state = {
        "blueprint": {"plot_points": ["point1", "point2"]}
    }
    
    result = await manager.node_audit_plot(state)
    
    assert result["audit_results"] == [{"consistent": True, "score": 0.9}]
    assert result["is_consistent"] == True
    assert result["status"] == "audit_completed"


@pytest.mark.asyncio
async def test_node_expand_scenes():
    """node_expand_scenesのテスト"""
    mock_engine = MagicMock()
    
    manager = PlotGraphManager(mock_engine)
    
    state = {
        "blueprint": {
            "scenes": [
                {"title": "Scene 1", "content": "Content 1"},
                {"title": "Scene 2", "content": "Content 2"}
            ]
        }
    }
    
    result = await manager.node_expand_scenes(state)
    
    assert result["scenes"] == [
        {"title": "Scene 1", "content": "Content 1"},
        {"title": "Scene 2", "content": "Content 2"}
    ]
    assert result["status"] == "scenes_expanded"


@pytest.mark.asyncio
async def test_node_save_plot():
    """node_save_plotのテスト"""
    mock_engine = MagicMock()
    mock_engine.repo = MagicMock()
    mock_engine.repo.create_or_replace_plot = AsyncMock()
    
    manager = PlotGraphManager(mock_engine)
    
    state = {
        "book_id": 1,
        "ep_num": 2,
        "branch_id": 3,
        "blueprint": {"act": 1},
        "scenes": [{"title": "Test Scene"}]
    }
    
    result = await manager.node_save_plot(state)
    
    assert result["status"] == "completed"
    assert "final_plot" in result
    assert result["final_plot"]["book_id"] == 1
    assert result["final_plot"]["ep_num"] == 2
    assert result["final_plot"]["branch_id"] == 3
    assert result["final_plot"]["blueprint"] == {"act": 1}
    assert result["final_plot"]["scenes"] == [{"title": "Test Scene"}]
    
    # リポジトリのメソッドが呼ばれたことを確認
    mock_engine.repo.create_or_replace_plot.assert_called_once()
    call_args = mock_engine.repo.create_or_replace_plot.call_args[0][0]
    assert call_args["book_id"] == 1
    assert call_args["ep_num"] == 2
    assert call_args["branch_id"] == 3
    assert call_args["blueprint"] == {"act": 1}
    assert call_args["scenes"] == [{"title": "Test Scene"}]


def test_should_retry_blueprint():
    """should_retry_blueprintのテスト（常に"proceed"を返す）"""
    mock_engine = MagicMock()
    manager = PlotGraphManager(mock_engine)
    
    state = {}  # どんな状態でも
    assert manager.should_retry_blueprint(state) == "proceed"


def test_plot_langgraph_state_structure():
    """PlotLangGraphで使用される状態の構造をテスト"""
    # PlotGraphManager.WorkflowStateは実際にはgraph_state.WorkflowStateを使用
    from src.backend.workflows.graph_state import WorkflowState
    
    state: WorkflowState = {
        "book_id": 1,
        "ep_num": 1,
        "branch_id": 1,
        "context_alignment": {},
        "blueprint": {},
        "final_plot": {},
        "audit_results": [],
        "is_consistent": True,
        "retry_count": 0,
        "max_retries": 3,
        "status": "starting"
    }
    
    assert state["book_id"] == 1
    assert state["ep_num"] == 1
    assert state["branch_id"] == 1
    assert state["context_alignment"] == {}
    assert state["blueprint"] == {}
    assert state["final_plot"] == {}
    assert state["audit_results"] == []
    assert state["is_consistent"] == True
    assert state["retry_count"] == 0
    assert state["max_retries"] == 3
    assert state["status"] == "starting"