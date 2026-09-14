import pytest
from src.services.billing.cost_budget_guard import CostBudgetConfig
from src.services.billing.token_budget_tracker import TokenBudgetTracker, CostBudgetExceededError

def test_token_budget_tracker_within_limit():
    config = CostBudgetConfig(max_tokens_per_episode=1000)
    tracker = TokenBudgetTracker(config)
    tracker.add_usage(300, 200)
    assert tracker.total_tokens == 500
    assert tracker.is_within_budget() is True

def test_token_budget_tracker_exceed_limit_raises_error():
    config = CostBudgetConfig(max_tokens_per_episode=1000)
    tracker = TokenBudgetTracker(config)
    tracker.add_usage(600, 300)  # 900
    with pytest.raises(CostBudgetExceededError):
        tracker.add_usage(100, 100)  # 1100 -> 超過
