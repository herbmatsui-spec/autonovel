import asyncio
import pytest
from src.llm.circuit_breaker import LLMCircuitBreaker
from src.llm.resilient_gateway import ResilientLLMGateway
from tests.fixtures.chaos_injector import ChaosInjector


@pytest.mark.asyncio
async def test_chaos_llm_resilience():
    # サーキットブレーカーとフォールバックチェーンの耐久テスト
    cb = LLMCircuitBreaker(failure_threshold=2, cooldown_seconds=0.2)
    injector = ChaosInjector(failure_rate=1.0)  # 必ず主プロバイダを落とす

    async def mock_primary(prompt, **kwargs):
        await injector.maybe_fail("openai")
        return "primary success"

    async def mock_secondary(prompt, **kwargs):
        return "fallback success from gemini"

    providers = {
        "openai": mock_primary,
        "gemini": mock_secondary,
    }

    fallback_policy = {
        "openai": ["gemini"],
    }

    gateway = ResilientLLMGateway(
        circuit_breaker=cb,
        providers=providers,
        default_provider="openai",
        fallback_policy=fallback_policy,
    )

    # 1. 主プロバイダがカオス注入で失敗しても、Geminiへ自動フェイルオーバーして完遂
    res = await gateway.generate_text("プロットを生成して")
    assert res == "fallback success from gemini"
    assert cb.get_state("openai").state.value in ("open", "closed")
