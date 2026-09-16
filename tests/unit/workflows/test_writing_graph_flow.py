import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.backend.workflows.writing_langgraph import WritingGraphManager


@pytest.mark.asyncio
async def test_writing_graph_complete_flow():
    """Writing LangGraphの正常系実行フローをテスト"""
    # キャッシュをクリアして一貫したテスト条件を確保
    WritingGraphManager.clear_gen_ctx_cache()

    # モックマネージャーを作成
    mock_manager = MagicMock()

    # 各ノードのモックを設定
    mock_manager._phase_prepare_context = AsyncMock(return_value=(
        "fake_gen_ctx", True, False, False, 50
    ))
    mock_manager._phase_drafting = AsyncMock(return_value=(
        "Completed draft content " * 10,  # 230+文字
        {"words": 230}
    ))
    mock_manager._phase_audit = AsyncMock(return_value=(
        True, 0.85, True, "OK", []
    ))
    mock_manager._phase_critic = AsyncMock(return_value=False)  # リトライ不要
    mock_manager._phase_healing = AsyncMock(return_value=(
        "healed content", True, "Fixed"
    ))
    mock_manager._run_dogfeeding_loop = AsyncMock(return_value=True)
    mock_manager._register_lazy_patch = AsyncMock()

    # 他の必要なモック
    mock_manager.narrative = MagicMock()
    mock_manager.narrative.get_integrity_threshold = MagicMock(return_value=0.7)
    mock_manager.repo = None  # ユーザーレビューなし

    # WritingGraphManagerのインスタンスを作成
    manager = WritingGraphManager(mock_manager)

    # langgraphが利用できない場合のフォールバックパスをテストするため、
    # あえてHAS_LANGGRAPHをFalseにする
    with patch('src.backend.workflows.writing_langgraph.HAS_LANGGRAPH', False):
        # runメソッドを実行（フォールバックパスが使用される）
        draft, meta, is_ok = await manager.run(
            ep_num=1,
            ctx={"genre_str": "fantasy", "plot": MagicMock(detailed_blueprint="blueprint")},
            sys_inst="System instruction",
            fw_prompt="Write a story",
            passion=0.8,
            is_easy_mode=False
        )

        # アサーション
        assert isinstance(draft, str)
        assert len(draft) > 0
        assert isinstance(meta, dict)
        assert is_ok  # すべてのチェックがパスしたはず

        # 各フェーズが呼ばれたことを確認
        mock_manager._phase_prepare_context.assert_called_once()
        mock_manager._phase_drafting.assert_called_once()
        mock_manager._phase_audit.assert_called_once()
        # criticはトリガーされないはず（should_heavy_auditがFalseのため）
        mock_manager._phase_critic.assert_not_called()
        mock_manager._phase_healing.assert_not_called()  # healingも不要
        mock_manager._run_dogfeeding_loop.assert_called_once()


@pytest.mark.asyncio
async def test_writing_graph_flow_with_mocked_workflow():
    """モックしたワークフローでフローをテスト（Step 3の意図に近いテスト）"""
    # WritingGraphManagerのインスタンスを作成
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)

    # langgraphが利用可能な状態をシミュレート
    # workflow属性にモックを直接設定
    mock_workflow = MagicMock()
    mock_workflow.ainvoke = AsyncMock(return_value={
        "draft_content": "完成した第1話原稿",
        "final_meta": {"score": 85},
        "is_integrity_ok": True,
        "is_causal_ok": True,
        "status": "completed"
    })
    manager.workflow = mock_workflow

    # 初期状態を作成する内部メソッドもモック
    initial_state = {
        "ep_num": 1,
        "passion": 0.8,
        "is_easy_mode": False,
        "context": {"genre_str": "fantasy"},
        "sys_inst": "System instruction",
        "fw_prompt": "Write a story",
        "ac_iter": 0,
        "max_ac_iter": 2,
        "should_heavy_audit": True,
        "should_dogfeed": True,
        "should_beat_decompose": False,
        "gen_ctx": None,
        "draft_content": "",
        "final_meta": {},
        "is_integrity_ok": False,
        "is_causal_ok": False,
        "causal_reason": "",
        "failures": [],
        "status": "pending",
        "patch_review_id": None,
        "review_status": None,
        "requires_user_review": False
    }

    # _create_initial_stateをモック
    with patch.object(manager, '_create_initial_state', return_value=initial_state):
        # runメソッドを実行
        draft, meta, is_ok = await manager.run(
            ep_num=1,
            ctx={"genre_str": "fantasy", "plot": MagicMock(detailed_blueprint="blueprint")},
            sys_inst="System instruction",
            fw_prompt="Write a story",
            passion=0.8,
            is_easy_mode=False
        )

        # アサーション（計画書の例に合わせる）
        assert isinstance(draft, str)
        assert "完成した第1話原稿" in draft
        assert isinstance(meta, dict)
        assert meta.get("score") == 85
        assert is_ok

        # ainvokeが呼ばれたことを確認
        mock_workflow.ainvoke.assert_called_once()

        # 渡された引数を確認
        call_args = mock_workflow.ainvoke.call_args[0][0]
        assert call_args == initial_state
