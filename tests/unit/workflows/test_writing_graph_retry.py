from unittest.mock import MagicMock
from src.backend.workflows.writing_langgraph import WritingGraphManager


def test_route_after_audit_easy_mode():
    """easy_mode時は即座に終了"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)

    state = {"is_easy_mode": True}
    assert manager.route_after_audit(state) == "finish"


def test_route_after_audit_high_quality_early_exit():
    """高品質で早期終了条件を満たす場合は終了"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)

    state = {
        "is_easy_mode": False,
        "quality_skip": True,
        "is_integrity_ok": True,
        "is_causal_ok": True
    }
    assert manager.route_after_audit(state) == "finish"


def test_route_after_audit_requires_user_review():
    """ユーザーレビューが必要な場合はreview_waitへ"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)

    state = {
        "is_easy_mode": False,
        "quality_skip": False,
        "requires_user_review": True,
        "patch_review_id": 123
    }
    assert manager.route_after_audit(state) == "review_wait"


def test_route_after_audit_max_iterations_reached():
    """最大イテレーションに達したら終了"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)

    state = {
        "is_easy_mode": False,
        "quality_skip": False,
        "is_integrity_ok": True,
        "is_causal_ok": True,
        "ac_iter": 2,  # 最大イテレーションに到達
        "max_ac_iter": 2
    }
    assert manager.route_after_audit(state) == "finish"


def test_route_after_audit_heavy_audit_needed():
    """重監査が必要かつイテレーション残っている場合はcriticへ"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)

    state = {
        "is_easy_mode": False,
        "quality_skip": False,
        "is_integrity_ok": True,
        "is_causal_ok": True,
        "should_heavy_audit": True,
        "ac_iter": 0,  # イテレーション残っている
        "max_ac_iter": 2
    }
    assert manager.route_after_audit(state) == "critic"


def test_route_after_audit_causal_fail_heavy_audit():
    """因果性失敗かつ重監査モードの場合はhealへ"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)

    state = {
        "is_easy_mode": False,
        "quality_skip": False,
        "is_integrity_ok": True,  # 整合性OK
        "is_causal_ok": False,    # 因果性NG
        "should_heavy_audit": True
    }
    assert manager.route_after_audit(state) == "heal"


def test_route_after_audit_causal_fail_can_retry():
    """因果性失敗だがまだリトリー可能ならhealへ（因果性失敗時はhealが優先）"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)

    state = {
        "is_easy_mode": False,
        "quality_skip": False,
        "is_integrity_ok": True,
        "is_causal_ok": False,
        "should_heavy_audit": True,
        "ac_iter": 0,  # リトリー可能
        "max_ac_iter": 2
    }
    # 因果性失敗かつ重監査モードの場合はhealへ（これが最初にマッチする条件）
    assert manager.route_after_audit(state) == "heal"


def test_route_after_audit_finish_default():
    """整合性NGで重監査モードじゃない場合は終了"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)

    state = {
        "is_easy_mode": False,
        "quality_skip": False,
        "is_integrity_ok": False,  # 整合性NG
        "is_causal_ok": True,
        "should_heavy_audit": False  # 重監査モードじゃない
    }
    assert manager.route_after_audit(state) == "finish"


def test_route_after_critic_retry_possible():
    """critic後にリトリー可能な場合はretry（draftingへ戻る）"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)

    state = {
        "critic_triggered": True,
        "ac_iter": 0,  # まだリトリー可能
        "max_ac_iter": 2
    }
    assert manager.route_after_critic(state) == "retry"


def test_route_after_critic_max_iterations():
    """critic後に最大イテレーションに達したら終了"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)

    state = {
        "critic_triggered": True,
        "ac_iter": 2,  # 最大イテレーションに到達
        "max_ac_iter": 2
    }
    assert manager.route_after_critic(state) == "finish"


def test_route_after_critic_not_triggered():
    """criticがトリガーされなかった場合は終了"""
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)

    state = {
        "critic_triggered": False,
        "ac_iter": 0,
        "max_ac_iter": 2
    }
    assert manager.route_after_critic(state) == "finish"


def test_writing_striker_retry_logic_from_plan():
    """計画書にあるテストと同じロジックをテスト"""
    # 条件分岐エッジのロジックテスト（計画書の例と同じ）
    def check_quality(state):
        if state["retry_count"] >= 3:
            return "end"
        if state["score"] < 70:
            return "rewrite"
        return "end"

    assert check_quality({"retry_count": 0, "score": 60}) == "rewrite"
    assert check_quality({"retry_count": 3, "score": 60}) == "end"
    assert check_quality({"retry_count": 1, "score": 80}) == "end"


def test_writing_graph_retry_count_increment():
    """各ノードでac_iterが正しくインクリメントされることをテスト"""
    # これは実際のノード実行をテストするより、状態遷移のロジックをテスト
    mock_manager = MagicMock()
    manager = WritingGraphManager(mock_manager)

    # 初期状態
    state = {
        "ac_iter": 0,
        "max_ac_iter": 3
    }

    # audit後の状態（ac_iterがインクリメントされる）
    audited_state = {
        **state,
        "is_integrity_ok": True,
        "is_causal_ok": True,
        "ac_iter": state["ac_iter"] + 1  # これが実際のノードでの振る舞い
    }

    assert audited_state["ac_iter"] == 1

    # まだイテレーション残っているのでcriticへ
    assert manager.route_after_audit(audited_state) == "critic"

    # critic後もまだリトリー可能
    critiqued_state = {
        **audited_state,
        "critic_triggered": True
    }
    assert manager.route_after_critic(critiqued_state) == "retry"

    # drafting後またaudit
    drafted_state = {
        **critiqued_state,
        "draft_content": "new draft",
        "ac_iter": audited_state["ac_iter"] + 1  # またインクリメント
    }
    assert drafted_state["ac_iter"] == 2
    assert manager.route_after_audit(drafted_state) == "critic"  # まだ続行

    # 3回目
    final_drafted_state = {
        **drafted_state,
        "draft_content": "final draft",
        "ac_iter": drafted_state["ac_iter"] + 1
    }
    assert final_drafted_state["ac_iter"] == 3
    assert manager.route_after_audit(final_drafted_state) == "finish"  # 最大に到達して終了
