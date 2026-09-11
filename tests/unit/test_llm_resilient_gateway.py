"""ResilientLLMGateway と LLMCircuitBreaker のユニットテスト"""

import asyncio
import pytest
from src.llm.circuit_breaker import LLMCircuitBreaker, CircuitState, ProviderHealthState
from src.llm.fallback_policy import FallbackPolicy, DEFAULT_FALLBACK_CHAINS
from src.llm.resilient_gateway import ResilientLLMGateway, normalize_schema_prompt
from unittest.mock import AsyncMock, MagicMock


class TestProviderHealthState:
    def test_default_state(self):
        state = ProviderHealthState("test")
        assert state.provider_name == "test"
        assert state.state == CircuitState.CLOSED
        assert state.failure_count == 0
        assert state.success_count == 0


class TestLLMCircuitBreaker:
    def test_initial_can_execute(self):
        cb = LLMCircuitBreaker()
        assert cb.can_execute("openai") is True

    def test_record_failure_opens_circuit(self):
        cb = LLMCircuitBreaker(failure_threshold=2, timeout_seconds=60)
        cb.record_failure("openai")
        assert cb.can_execute("openai") is True
        cb.record_failure("openai")
        assert cb.can_execute("openai") is False
        state = cb.get_state("openai")
        assert state.state == CircuitState.OPEN

    def test_half_open_after_cooldown(self):
        cb = LLMCircuitBreaker(failure_threshold=1, timeout_seconds=1, half_open_max_calls=1)
        cb.record_failure("gemini")
        assert cb.can_execute("gemini") is False
        # クールダウン待機（同期テストでは時間を進められないためモック不可）
        # 実装依存の内部状態を直接書き換えてテスト
        state = cb.get_state("gemini")
        state.state = CircuitState.HALF_OPEN
        state.success_count = 0
        # 1 回目の呼び出しは許可
        assert cb.can_execute("gemini") is True
        # 2 回目は HALF_OPEN の max_calls=1 なので不可
        assert cb.can_execute("gemini") is False

    def test_record_success_closes_circuit(self):
        cb = LLMCircuitBreaker(failure_threshold=2, timeout_seconds=60)
        cb.record_failure("claude")
        cb.record_failure("claude")
        assert cb.can_execute("claude") is False
        cb.record_success("claude")
        # OPEN 状態では成功しても CLOSED には戻らない（仕様）
        assert cb.can_execute("claude") is False
        # HALF_OPEN で成功すれば CLOSED に戻る
        state = cb.get_state("claude")
        state.state = CircuitState.HALF_OPEN
        state.success_count = 0
        cb.record_success("claude")
        assert cb.can_execute("claude") is True

    def test_reset(self):
        cb = LLMCircuitBreaker()
        cb.record_failure("openai")
        cb.record_failure("openai")
        cb.reset("openai")
        assert cb.can_execute("openai") is True


class TestFallbackPolicy:
    def test_default_chains_loaded(self):
        policy = FallbackPolicy()
        seq = policy.get_fallback_sequence("claude")
        assert seq == ["openai", "gemini", "mock"]

    def test_custom_chain(self):
        custom = {"myprov": ["fallback1", "fallback2"]}
        policy = FallbackPolicy(custom)
        seq = policy.get_fallback_sequence("myprov")
        assert seq == ["fallback1", "fallback2"]


class TestResilientLLMGateway:
    @pytest.mark.asyncio
    async def test_generate_text_success_first_provider(self):
        mock_provider = AsyncMock()
        mock_provider.generate_text.return_value = "ok"
        gateway = ResilientLLMGateway(
            providers={"openai": mock_provider},
            default_provider="openai",
        )
        result = await gateway.generate_text("prompt", primary_provider="openai")
        assert result == "ok"
        mock_provider.generate_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generate_text_fails_over_to_fallback(self):
        failing = AsyncMock()
        failing.generate_text.side_effect = RuntimeError("down")
        ok = AsyncMock()
        ok.generate_text.return_value = "fallback ok"
        gateway = ResilientLLMGateway(
            providers={"openai": failing, "gemini": ok},
            default_provider="openai",
        )
        result = await gateway.generate_text("prompt", primary_provider="openai")
        assert result == "fallback ok"
        failing.generate_text.assert_awaited_once()
        ok.generate_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rate_limit_fallback(self):
        class RateLimitError(Exception):
            pass
        failing = AsyncMock()
        failing.generate_text.side_effect = RateLimitError("429")
        ok = AsyncMock()
        ok.generate_text.return_value = "after rate limit"
        gateway = ResilientLLMGateway(
            providers={"openai": failing, "gemini": ok},
            default_provider="openai",
            backoff_base_seconds=0,
            max_backoff_seconds=0,
        )
        result = await gateway.generate_text("prompt", primary_provider="openai")
        assert result == "after rate limit"

    def test_normalize_schema_prompt(self):
        class DummySchema:
            def model_json_schema(self):
                return {"type": "object", "properties": {"x": {"type": "int"}}}
        out = normalize_schema_prompt("hello", DummySchema())
        assert "JSON" in out or "json" in out
        assert "x" in out


if __name__ == "__main__":
    pytest.main([__file__, "-v"])