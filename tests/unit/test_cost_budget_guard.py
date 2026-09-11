import pytest
from src.services.cost_analytics import CostCalculator
from src.services.cost_budget_guard import CostBudgetGuard, BudgetStatus

class TestCostBudgetGuard:
    def test_initialization(self):
        calc = CostCalculator()
        guard = CostBudgetGuard(calc, 100.0)
        assert isinstance(guard, CostBudgetGuard)
        assert guard.budget_limit == 100.0
    
    def test_budget_status_normal(self):
        calc = CostCalculator()
        guard = CostBudgetGuard(calc, 1000.0)  # High budget
        status = guard.check_budget_status(1)
        assert status == BudgetStatus.NORMAL
    
    def test_budget_status_warning(self):
        calc = CostCalculator()
        guard = CostBudgetGuard(calc, 10.0)  # Budget of 10.0
        # With book_id=15, cost = 15 * 0.5 = 7.5, ratio = 7.5/10.0 = 0.75 (75%) -> WARNING
        status = guard.check_budget_status(15)
        assert status == BudgetStatus.WARNING
    
    def test_budget_status_exceeded(self):
        calc = CostCalculator()
        guard = CostBudgetGuard(calc, 1.0)  # Budget of 1.0
        # With book_id=2, cost = 2 * 0.5 = 1.0, ratio = 1.0/1.0 = 1.0 (100%) -> EXCEEDED
        status = guard.check_budget_status(2)
        assert status == BudgetStatus.EXCEEDED
    
    def test_recommended_model_for_task(self):
        calc = CostCalculator()
        guard = CostBudgetGuard(calc, 1000.0)
        model = guard.get_recommended_model_for_task("writing", 1)
        # Should return a model name
        assert isinstance(model, str)