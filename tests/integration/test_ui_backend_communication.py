"""
tests/integration/test_ui_backend_communication.py

UI層 (streamlit_app) がバックエンド API クライアント経由で
バックエンドと通信できることを確認するインテグレーションテスト。

対象:
  1. UI (streamlit_app.api_client) が src.shared.resilient_http を直接 import できるか
  2. タスク生成 (plan / plot / writing) が正しいエンドポイントへ送信されるか
  3. ステータス取得ができるか
  4. プログレス更新 (stop) ができるか
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_resilient_client(monkeypatch):
    """ResilientHttpClient をモックし、APIクライアントが呼び出す
    request() が正常なレスポンスを返すようにする。"""
    client = MagicMock()
    client.request = AsyncMock()

    def _make_response(payload):
        resp = MagicMock()
        resp.json.return_value = payload
        resp.status_code = 200
        # api_client はレスポンスに対して .get() を呼ぶため、dict ライクに振る舞わせる
        resp.get.side_effect = lambda k, d=None: payload.get(k, d)
        return resp

    # デフォルトは task_id を含むレスポンス
    client.request.return_value = _make_response({"task_id": "task-123"})

    # get_client() がこのモックを返すように差し替え
    import streamlit_app.api_client as api_client
    monkeypatch.setattr(api_client, "get_client", lambda: client)
    return client


def test_ui_imports_backend_http_client():
    """UI層が src.shared.resilient_http.ResilientHttpClient を直接 import できること
    (リファクタリング目標: UI層は src のビジネスロジックを直接 import 可能)。"""
    from src.shared.resilient_http import ResilientHttpClient
    from streamlit_app.api_client import get_client

    assert callable(get_client)
    assert ResilientHttpClient is not None


def test_start_plan_generation_sends_post(mock_resilient_client):
    """plan生成が POST /plan/generate へ送信され task_id を返すこと。"""
    from streamlit_app.api_client import start_plan_generation

    task_id = start_plan_generation(genre="fantasy", theme="勇者")

    mock_resilient_client.request.assert_awaited_once_with(
        method="POST",
        path="/plan/generate",
        json={"genre": "fantasy", "theme": "勇者"},
        timeout=10.0,
    )
    assert task_id == "task-123"


def test_start_plot_expansion_sends_post(mock_resilient_client):
    """plot展開が POST /plot/expand へ送信されること。"""
    from streamlit_app.api_client import start_plot_expansion

    task_id = start_plot_expansion(book_id=1)

    mock_resilient_client.request.assert_awaited_once_with(
        method="POST",
        path="/plot/expand",
        json={"book_id": 1},
        timeout=10.0,
    )
    assert task_id == "task-123"


def test_start_episode_writing_sends_post(mock_resilient_client):
    """episode執筆が POST /writing/start へ送信されること。"""
    from streamlit_app.api_client import start_episode_writing

    task_id = start_episode_writing(book_id=2, episode=3)

    mock_resilient_client.request.assert_awaited_once_with(
        method="POST",
        path="/writing/start",
        json={"book_id": 2, "episode": 3},
        timeout=10.0,
    )
    assert task_id == "task-123"


def test_start_erotic_refinement_sends_post(mock_resilient_client):
    """官能研磨が POST /refine_erotic へ送信されること。"""
    from streamlit_app.api_client import start_erotic_refinement

    task_id = start_erotic_refinement(
        api_key="k", config={}, book_id=5, ep_num=7,
        intensity=3, platform_preset="kakuyomu_romance",
    )

    mock_resilient_client.request.assert_awaited_once_with(
        method="POST",
        path="/refine_erotic",
        json={
            "api_key": "k", "config": {}, "book_id": 5, "ep_num": 7,
            "intensity": 3, "platform_preset": "kakuyomu_romance",
        },
        timeout=10.0,
    )
    assert task_id == "task-123"


def test_get_task_status_sends_get(mock_resilient_client):
    """タスクステータス取得が GET /tasks/{id} へ送信されること。"""
    from streamlit_app.api_client import get_task_status

    status = get_task_status("task-123", timeout=5.0)

    mock_resilient_client.request.assert_awaited_once_with(
        method="GET",
        path="/tasks/task-123",
        json={},
        timeout=5.0,
    )
    # get_task_status はレスポンスオブジェクトを返す (api_client の仕様)
    assert status.get("task_id") == "task-123"


def test_stop_task_sends_post(mock_resilient_client):
    """タスク停止が POST /tasks/{id}/stop へ送信されること。"""
    from streamlit_app.api_client import stop_task

    stop_task("task-123")

    mock_resilient_client.request.assert_awaited_once_with(
        method="POST",
        path="/tasks/task-123/stop",
        json={},
        timeout=10.0,
    )


def test_request_failure_propagates_error(mock_resilient_client):
    """バックエンド通信失敗時に例外が伝播すること。"""
    import pytest as _pytest

    from streamlit_app.api_client import get_task_status

    mock_resilient_client.request.side_effect = RuntimeError("backend down")

    with _pytest.raises(RuntimeError):
        get_task_status("task-123")
