import pytest
from unittest.mock import AsyncMock
from src.services.llm.provider_failover import ProviderFailoverManager
from src.services.billing.cost_budget_guard import CostBudgetConfig
from src.services.billing.token_budget_tracker import TokenBudgetTracker, CostBudgetExceededError

@pytest.mark.asyncio
async def test_failover_and_budget_integration():
    manager = ProviderFailoverManager()
    tracker = TokenBudgetTracker(CostBudgetConfig(max_tokens_per_episode=500))

    # Primary (Gemini) はエラー
    primary_mock = AsyncMock(side_effect=RuntimeError("503 Service Unavailable"))
    # Fallback (OpenAI) は成功
    fallback_mock = AsyncMock(return_value="Fallback text")

    # フェイルオーバー実行
    res, provider = await manager.execute_with_fallback("gemini", "openai", primary_mock, fallback_mock)
    assert res == "Fallback text"
    assert provider == "openai"

    # トークン加算して予算超過チェック
    tracker.add_usage(300, 100)  # 400
    with pytest.raises(CostBudgetExceededError):
        tracker.add_usage(100, 50)  # 550 > 500
