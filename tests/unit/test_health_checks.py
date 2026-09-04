"""ヘルスチェックモジュールのユニットテスト。"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.backend.health.checks import HealthStatus, check_llm_gateway


@pytest.mark.asyncio
async def test_check_llm_gateway_returns_not_configured_when_no_key():
    result = await check_llm_gateway(api_key=None)
    assert result.status == HealthStatus.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_check_llm_gateway_returns_not_configured_for_dummy_key():
    result = await check_llm_gateway(api_key="DUMMY")
    assert result.status == HealthStatus.NOT_CONFIGURED


@pytest.mark.asyncio
async def test_check_llm_gateway_returns_not_configured_when_disabled(monkeypatch):
    monkeypatch.setenv("KAKU_HEALTH_CHECK_LLM", "false")
    result = await check_llm_gateway(api_key="test-key")
    assert result.status == HealthStatus.NOT_CONFIGURED
    assert "disabled" in result.details


@pytest.mark.asyncio
async def test_check_llm_gateway_instantiates_factory_with_cooldown(monkeypatch):
    """LLMProviderFactory が cooldown 付きで生成され、正常応答を返せること。"""

    async def fake_generate_text(*args, **kwargs):
        return "ok"

    fake_factory = MagicMock()
    fake_factory.generate_text = fake_generate_text

    def fake_factory_ctor(genai_client, cooldown):
        assert genai_client is not None
        assert cooldown is not None
        return fake_factory

    monkeypatch.setattr(
        "src.core.llm_gateway.LLMProviderFactory",
        fake_factory_ctor,
    )
    monkeypatch.setattr(
        "src.core.llm_gateway.create_genai_client",
        lambda api_key: MagicMock(),
    )

    result = await check_llm_gateway(api_key="real-key-123")
    assert result.status == HealthStatus.OK
    assert "response_len=2" in result.details


@pytest.mark.asyncio
async def test_check_llm_gateway_returns_error_on_factory_exception(monkeypatch):
    def factory_raises(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(
        "src.core.llm_gateway.LLMProviderFactory",
        factory_raises,
    )
    monkeypatch.setattr(
        "src.core.llm_gateway.create_genai_client",
        lambda api_key: MagicMock(),
    )

    result = await check_llm_gateway(api_key="real-key-123")
    assert result.status == HealthStatus.ERROR
    assert "boom" in result.error
