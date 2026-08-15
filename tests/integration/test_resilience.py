"""
tests/integration/test_resilience.py

機能9（オフライン／低帯域耐障害モード）のテスト。
resilience サービスの状態判定と system ルーターのエンドポイントを確認する。
"""


from src.backend.routers import system as system_router
from src.services import resilience


def test_offline_mode_flag_default_false(monkeypatch):
    monkeypatch.delenv("OFFLINE_MODE", raising=False)
    assert resilience.is_offline_mode_enabled() is False


def test_offline_mode_flag_true(monkeypatch):
    monkeypatch.setenv("OFFLINE_MODE", "true")
    assert resilience.is_offline_mode_enabled() is True


def test_get_system_status_keys(monkeypatch):
    monkeypatch.delenv("OFFLINE_MODE", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    status = resilience.get_system_status()
    assert "mode" in status
    assert status["database"] in ("ok", "error")
    # キー未設定時は gemini=disabled
    assert status["gemini"] == "disabled"


def test_system_status_endpoint():
    import asyncio

    status = asyncio.get_event_loop().run_until_complete(system_router.system_status())
    assert "mode" in status
    assert "database" in status
    assert "gemini" in status


def test_offline_flag_endpoint():
    import asyncio

    res = asyncio.get_event_loop().run_until_complete(system_router.offline_flag())
    assert "offline_mode_enabled" in res
    assert "cache_first" in res
