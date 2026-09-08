import pytest
from src.backend.tasks.huey import huey, execute_agent_node_task, check_huey_health


def test_huey_health_check():
    """Step 42の検証: Huey health check"""
    health = check_huey_health()
    assert health["status"] == "healthy"
    assert "backend" in health
    assert "pending_tasks" in health


def test_execute_agent_node_task_sync():
    """Step 39-40の検証: execute_agent_node_task の実行"""
    # 即時モードでタスクを実行
    orig_immediate = huey.immediate
    try:
        huey.immediate = True
        res_ping = execute_agent_node_task("ping", {"msg": "hello"})
        # immediate mode ではタスク関数が直接結果またはResultを返す
        if hasattr(res_ping, "get"):
            result_val = res_ping.get(blocking=True)
        else:
            result_val = res_ping

        assert result_val["status"] == "pong"
        assert result_val["payload"]["msg"] == "hello"

        res_echo = execute_agent_node_task("generic_agent", {"k1": "v1", "k2": "v2"})
        if hasattr(res_echo, "get"):
            echo_val = res_echo.get(blocking=True)
        else:
            echo_val = res_echo

        assert echo_val["node"] == "generic_agent"
        assert echo_val["status"] == "completed"
    finally:
        huey.immediate = orig_immediate


@pytest.mark.asyncio
async def test_async_wait_huey_result():
    """Step 43の検証: async_wait_huey_result"""
    from src.backend.tasks.huey import async_wait_huey_result
    from unittest.mock import MagicMock

    # 1. 既に値がある場合
    mock_res = MagicMock()
    mock_res.get.return_value = {"ok": True}
    val = await async_wait_huey_result(mock_res, timeout=2.0)
    assert val == {"ok": True}

    # 2. タイムアウトする場合
    mock_res_timeout = MagicMock()
    mock_res_timeout.get.return_value = None
    with pytest.raises(TimeoutError):
        await async_wait_huey_result(mock_res_timeout, timeout=0.1, poll_interval=0.02)


def test_execute_agent_node_task_error_handling():
    """Step 44の検証: エラー発生時の安全ハンドリング"""
    orig_immediate = huey.immediate
    try:
        huey.immediate = True
        res = execute_agent_node_task("raise_error", {"error_msg": "Boom!"})
        val = res.get(blocking=True) if hasattr(res, "get") else res
        assert val["node"] == "raise_error"
        assert val["status"] == "failed"
        assert "Boom!" in val["error"]
    finally:
        huey.immediate = orig_immediate


def test_system_router_huey_health():
    """Step 46-47の検証: system.py / server.py の Huey 連携"""
    from src.backend.routers.system import router
    routes = [r.path for r in router.routes]
    assert any("huey/health" in r for r in routes)
