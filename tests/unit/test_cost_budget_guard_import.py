from src.services.cost_analytics import CostCalculator
from src.services.cost_budget_guard import CostBudgetGuard, BudgetStatus

# Test that CostCalculator can be instantiated
calc = CostCalculator()
print("CostCalculator imported and instantiated successfully")

# Test that CostBudgetGuard can be instantiated
guard = CostBudgetGuard(calc, 10.0)
print("CostBudgetGuard instantiated successfully")
print(f"Budget limit: {guard.budget_limit}")