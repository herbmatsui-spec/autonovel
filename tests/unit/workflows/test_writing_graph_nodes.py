import pytest
from unittest.mock import AsyncMock, MagicMock
from src.backend.workflows.writing_langgraph import WritingGraphManager, WritingGraphState


@pytest.mark.asyncio
async def test_node_prepare():
    """node_prepareのテスト"""
    # モックマネージャーを作成
    mock_manager = MagicMock()
    mock_manager._phase_prepare_context = AsyncMock(return_value=(
        "fake_gen_ctx",  # gen_ctx
        True,            # should_dogfeed
        False,           # should_heavy_audit
        False,           # should_beat_decompose
        50               # ncs_score
    ))
    
    # WritingGraphManagerのインスタンスを作成
    manager = WritingGraphManager(mock_manager)
    
    # テスト状態
    state = {
        "ep_num": 1,
        "context": {"genre_str": "fantasy"},
        "sys_inst": "system instruction",
        "fw_prompt": "write a story",
        "is_easy_mode": False,
        "passion": 0.8
    }
    
    # node_prepareを実行
    result = await manager.node_prepare(state)
    
    # アサーション
    assert result["gen_ctx"] == "fake_gen_ctx"
    assert result["max_ac_iter"] == 2  # デフォルト値 (base_max from ProjectContext)
    assert result["should_heavy_audit"] == False
    assert result["should_dogfeed"] == True
    assert result["should_beat_decompose"] == False
    assert result["ac_iter"] == 0


@pytest.mark.asyncio
async def test_node_drafting_success():
    """node_draftingの成功ケースをテスト"""
    mock_manager = MagicMock()
    # 内容が100文字以上必要（node_drafting内のチェック）
    mock_manager._phase_drafting = AsyncMock(return_value=(
        "Generated draft content " * 10,  # 230文字以上
        {"words": 230}
    ))
    
    manager = WritingGraphManager(mock_manager)
    
    state = {
        "ep_num": 1,
        "context": {
            "plot": MagicMock(detailed_blueprint="blueprint text")
        },
        "passion": 0.5,
        "ac_iter": 0,
        "should_beat_decompose": False,
        "gen_ctx": "fake_gen_ctx"
    }
    
    result = await manager.node_drafting(state)
    
    assert result["draft_content"] == "Generated draft content " * 10
    assert result["final_meta"] == {"words": 230}


@pytest.mark.asyncio
async def test_node_drafting_failure():
    """node_draftingの失敗ケースをテスト（3回リトリー後に失敗）"""
    mock_manager = MagicMock()
    mock_manager._phase_drafting = AsyncMock(side_effect=Exception("Drafting failed"))
    
    manager = WritingGraphManager(mock_manager)
    
    state = {
        "ep_num": 1,
        "context": {
            "plot": MagicMock(detailed_blueprint="blueprint text")
        },
        "passion": 0.5,
        "ac_iter": 0,
        "should_beat_decompose": False,
        "gen_ctx": "fake_gen_ctx"
    }
    
    result = await manager.node_drafting(state)
    
    # 3回リトリー後に失敗すると空のコンテンツが返される
    assert result["draft_content"] == ""
    assert result["final_meta"] == {}


@pytest.mark.asyncio
async def test_node_audit_easy_mode():
    """easy_mode時のnode_auditをテスト"""
    mock_manager = MagicMock()
    
    manager = WritingGraphManager(mock_manager)
    
    state = {
        "ep_num": 1,
        "is_easy_mode": True,
        "ac_iter": 0
    }
    
    result = await manager.node_audit(state)
    
    assert result["is_integrity_ok"] == True
    assert result["is_causal_ok"] == True
    assert result["causal_reason"] == "easy_mode"
    assert result["failures"] == []
    assert result["ac_iter"] == 1  # ac_iterがインクリメントされる


@pytest.mark.asyncio
async def test_node_audit_success():
    """通常のnode_audit成功ケースをテスト"""
    mock_manager = MagicMock()
    mock_manager._phase_audit = AsyncMock(return_value=(
        True,   # is_integrity_ok
        0.8,    # rate
        True,   # is_causal_ok
        "OK",   # causal_reason
        []      # failures
    ))
    mock_manager.narrative = MagicMock()
    mock_manager.narrative.get_integrity_threshold = MagicMock(return_value=0.6)
    
    manager = WritingGraphManager(mock_manager)
    
    state = {
        "ep_num": 1,
        "context": {
            "genre_str": "fantasy",
            "prev_integrity": 100,
            "engine_key": "test",
            "plot": MagicMock(detailed_blueprint="blueprint")
        },
        "draft_content": "draft text",
        "final_meta": {},
        "is_easy_mode": False,
        "ac_iter": 0,
        "should_heavy_audit": False
    }
    
    result = await manager.node_audit(state)
    
    assert result["is_integrity_ok"] == True
    assert result["is_causal_ok"] == True
    assert result["causal_reason"] == "OK"
    assert result["rate"] == 0.8
    assert result["ac_iter"] == 1
    assert "threshold" in result
    assert "quality_skip" in result


@pytest.mark.asyncio
async def test_node_critic():
    """node_criticのテスト"""
    mock_manager = MagicMock()
    mock_manager._phase_critic = AsyncMock(return_value=True)  # triggered
    
    manager = WritingGraphManager(mock_manager)
    
    state = {
        "ac_iter": 0,
        "ep_num": 1,
        "draft_content": "draft",
        "context": {
            "plot": MagicMock(detailed_blueprint="blueprint")
        },
        "blueprint": "blueprint",
        "failures": [],
        "gen_ctx": "fake_gen_ctx"
    }
    
    result = await manager.node_critic(state)
    
    assert result["critic_triggered"] == True


@pytest.mark.asyncio
async def test_node_healing():
    """node_healingのテスト"""
    mock_manager = MagicMock()
    mock_manager._phase_healing = AsyncMock(return_value=(
        "healed content",  # content
        True,              # is_causal_ok
        "Fixed"            # causal_reason
    ))
    
    manager = WritingGraphManager(mock_manager)
    
    state = {
        "ep_num": 1,
        "draft_content": "original draft",
        "context": {
            "plot": MagicMock(detailed_blueprint="blueprint")
        },
        "blueprint": "blueprint",
        "causal_reason": "Original reason",
        "failures": [],
        "monitor": None
    }
    
    result = await manager.node_healing(state)
    
    assert result["draft_content"] == "healed content"
    assert result["is_causal_ok"] == True
    assert result["causal_reason"] == "Fixed"


@pytest.mark.asyncio
async def test_node_dogfeed_skipped():
    """should_dogfeedがFalseのときのnode_dogfeedをテスト（スキップされる）"""
    mock_manager = MagicMock()
    
    manager = WritingGraphManager(mock_manager)
    
    state = {
        "ep_num": 1,
        "draft_content": "draft",
        "passion": 0.5,
        "should_dogfeed": False,  # スキップされる条件
        "is_easy_mode": False,
        "ac_iter": 0,
        "max_ac_iter": 2,
        "gen_ctx": "fake_gen_ctx"
    }
    
    result = await manager.node_dogfeed(state)
    
    assert result["dogfeed_ok"] == True  # スキップ時にTrueが返される


@pytest.mark.asyncio
async def test_node_dogfeed_success():
    """node_dogfeedの成功ケースをテスト"""
    mock_manager = MagicMock()
    mock_manager._run_dogfeeding_loop = AsyncMock(return_value=True)
    
    manager = WritingGraphManager(mock_manager)
    
    state = {
        "ep_num": 1,
        "draft_content": "draft",
        "passion": 0.5,
        "should_dogfeed": True,
        "is_easy_mode": False,
        "ac_iter": 0,
        "max_ac_iter": 2,
        "gen_ctx": "fake_gen_ctx"
    }
    
    result = await manager.node_dogfeed(state)
    
    assert result["dogfeed_ok"] == True


@pytest.mark.asyncio
async def test_node_finalize():
    """node_finalizeのテスト"""
    mock_manager = MagicMock()
    mock_manager._register_lazy_patch = AsyncMock()
    
    manager = WritingGraphManager(mock_manager)
    
    state = {
        "ep_num": 1,
        "is_integrity_ok": True,
        "is_causal_ok": True,
        "dogfeed_ok": True,
        "is_easy_mode": False,
        "context": {"genre_str": "fantasy"},
        "rate": 0.85,
        "threshold": 0.7,
        "causal_reason": "OK",
        "ac_iter": 1
    }
    
    result = await manager.node_finalize(state)
    
    assert result["status"] == "completed"
    # _register_lazy_patchは呼ばれないはず（すべてOKなので）
    mock_manager._register_lazy_patch.assert_not_called()


def test_route_after_audit_easy_mode():
    """easy_mode時のroute_after_auditをテスト"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)
    
    state = {"is_easy_mode": True}
    assert manager.route_after_audit(state) == "finish"


def test_route_after_audit_high_quality():
    """高品質時のroute_after_auditをテスト（早期終了）"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)
    
    state = {
        "is_easy_mode": False,
        "quality_skip": True,
        "is_integrity_ok": True,
        "is_causal_ok": True
    }
    assert manager.route_after_audit(state) == "finish"


def test_route_after_audit_needs_review():
    """ユーザーレビューが必要な時のroute_after_auditをテスト"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)
    
    state = {
        "is_easy_mode": False,
        "quality_skip": False,
        "requires_user_review": True,
        "patch_review_id": 123
    }
    assert manager.route_after_audit(state) == "review_wait"


def test_route_after_critic_retry():
    """critic後にリトライすべき時のroute_after_criticをテスト"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)
    
    state = {
        "critic_triggered": True,
        "ac_iter": 0,
        "max_ac_iter": 2
    }
    assert manager.route_after_critic(state) == "retry"


def test_route_after_critic_finish():
    """critic後に終了すべき時のroute_after_criticをテスト"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)
    
    state = {
        "critic_triggered": True,
        "ac_iter": 2,  # max_ac_iterに到達
        "max_ac_iter": 2
    }
    assert manager.route_after_critic(state) == "finish"


def test_route_after_review_wait():
    """route_after_review_waitのテスト"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)
    
    # approved
    state = {"review_status": "approved"}
    assert manager.route_after_review_wait(state) == "approved"
    
    # rejected
    state = {"review_status": "rejected"}
    assert manager.route_after_review_wait(state) == "rejected"
    
    # revised
    state = {"review_status": "revised"}
    assert manager.route_after_review_wait(state) == "revised"
    
    # timeout
    state = {"review_status": "timeout"}
    assert manager.route_after_review_wait(state) == "timeout"


def test_writing_graph_state_typeddict():
    """WritingGraphStateの構造をテスト"""
    # WritingGraphStateはTypedDictなので、必須フィールがあるかチェック
    state: WritingGraphState = {
        "ep_num": 1,
        "passion": 0.5,
        "is_easy_mode": False,
        "context": {},
        "sys_inst": "",
        "fw_prompt": "",
        "ac_iter": 0,
        "max_ac_iter": 2,
        "gen_ctx": None,
        "draft_content": "",
        "final_meta": {},
        "is_integrity_ok": False,
        "is_causal_ok": False,
        "causal_reason": "",
        "failures": [],
        "patch_review_id": None,
        "review_status": None,
        "requires_user_review": False,
        "status": "pending"
    }
    
    # 必須フィールへのアクセス
    assert state["ep_num"] == 1
    assert state["passion"] == 0.5
    assert state["is_easy_mode"] == False
    assert state["context"] == {}
    assert state["sys_inst"] == ""
    assert state["fw_prompt"] == ""
    assert state["ac_iter"] == 0
    assert state["max_ac_iter"] == 2
    assert state["gen_ctx"] is None
    assert state["draft_content"] == ""
    assert state["final_meta"] == {}
    assert state["is_integrity_ok"] == False
    assert state["is_causal_ok"] == False
    assert state["causal_reason"] == ""
    assert state["failures"] == []
    assert state["patch_review_id"] is None
    assert state["review_status"] is None
    assert state["requires_user_review"] == False
    assert state["status"] == "pending"