import pytest
from src.services.cost_guard.budget_calculator import BudgetCalculator
from src.services.cost_guard.token_circuit_breaker import (
    TokenCircuitBreaker,
    BudgetExceededError,
)


def test_budget_calculator():
    estimate = BudgetCalculator.calculate_cost("gemini-2.5-flash", 10_000, 3_000)
    assert estimate.model == "gemini-2.5-flash"
    assert estimate.prompt_tokens == 10_000
    assert estimate.completion_tokens == 3_000
    # (10000/1M)*0.075 + (3000/1M)*0.30 = 0.00075 + 0.0009 = 0.00165 USD
    # 0.00165 * 150 = 0.2475 JPY
    assert estimate.cost_usd == 0.00165
    assert estimate.cost_jpy < 1.0


def test_circuit_breaker_pass():
    breaker = TokenCircuitBreaker(max_tokens_per_episode=1000, max_cost_jpy_per_episode=5.0)
    breaker.record_usage(500, 2.0)
    assert breaker.accumulated_tokens == 500
    assert breaker.accumulated_cost_jpy == 2.0


def test_circuit_breaker_token_exceeded():
    breaker = TokenCircuitBreaker(max_tokens_per_episode=1000, max_cost_jpy_per_episode=5.0)
    with pytest.raises(BudgetExceededError) as exc:
        breaker.record_usage(1001, 1.0)
    assert "Token budget exceeded" in str(exc.value)


def test_circuit_breaker_cost_exceeded():
    breaker = TokenCircuitBreaker(max_tokens_per_episode=50000, max_cost_jpy_per_episode=5.0)
    with pytest.raises(BudgetExceededError) as exc:
        breaker.record_usage(1000, 5.5)
    assert "Cost budget exceeded" in str(exc.value)


def test_circuit_breaker_reset():
    breaker = TokenCircuitBreaker(max_tokens_per_episode=1000, max_cost_jpy_per_episode=5.0)
    breaker.record_usage(500, 2.0)
    breaker.reset()
    assert breaker.accumulated_tokens == 0
    assert breaker.accumulated_cost_jpy == 0.0
