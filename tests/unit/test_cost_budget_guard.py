import pytest
from unittest.mock import AsyncMock, MagicMock
from src.services.cost_analytics import CostCalculator
from src.services.cost_budget_guard import CostBudgetGuard, BudgetStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class TestCostBudgetGuard:
    def test_initialization(self):
        calc = CostCalculator()
        guard = CostBudgetGuard(calc, 100.0)
        assert isinstance(guard, CostBudgetGuard)
        assert guard.budget_limit == 100.0

    @pytest.mark.asyncio
    async def test_budget_status_normal(self):
        calc = CostCalculator()
        guard = CostBudgetGuard(calc, 1000.0)  # High budget
        
        # Mock db_session to return low cost
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock the execute result for list_by_book query
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []  # No cost records = zero cost
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        status = await guard.check_budget_status_async(mock_session, 1)
        assert status == BudgetStatus.NORMAL

    @pytest.mark.asyncio
    async def test_budget_status_warning(self):
        calc = CostCalculator()
        guard = CostBudgetGuard(calc, 10.0)  # Budget of 10.0
        
        # Mock db_session to return cost that is 75% of budget (7.5)
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock the execute result for list_by_book query
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        
        # Create mock CostRecord objects
        mock_record = MagicMock()
        mock_record.total_tokens = 1000
        mock_record.est_cost_usd = 7.5
        mock_record.task_type = "writing"
        mock_record.created_at = None
        
        mock_scalars.all.return_value = [mock_record]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        status = await guard.check_budget_status_async(mock_session, 15)
        assert status == BudgetStatus.WARNING

    @pytest.mark.asyncio
    async def test_budget_status_exceeded(self):
        calc = CostCalculator()
        guard = CostBudgetGuard(calc, 1.0)  # Budget of 1.0
        
        # Mock db_session to return cost that is 100% of budget (1.0)
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock the execute result for list_by_book query
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        
        # Create mock CostRecord objects
        mock_record = MagicMock()
        mock_record.total_tokens = 2000
        mock_record.est_cost_usd = 1.0
        mock_record.task_type = "writing"
        mock_record.created_at = None
        
        mock_scalars.all.return_value = [mock_record]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        status = await guard.check_budget_status_async(mock_session, 2)
        assert status == BudgetStatus.EXCEEDED

    @pytest.mark.asyncio
    async def test_recommended_model_for_task(self):
        calc = CostCalculator()
        guard = CostBudgetGuard(calc, 1000.0)
        
        # Mock db_session for normal case (under 90%)
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Mock the execute result for list_by_book query
        mock_result = MagicMock()
        mock_scalars = MagicMock()
        
        # Create mock CostRecord objects
        mock_record = MagicMock()
        mock_record.total_tokens = 10000
        mock_record.est_cost_usd = 500.0  # 50% of budget
        mock_record.task_type = "writing"
        mock_record.created_at = None
        
        mock_scalars.all.return_value = [mock_record]
        mock_result.scalars.return_value = mock_scalars
        mock_session.execute.return_value = mock_result
        
        model = await guard.get_recommended_model_for_task_async(mock_session, "writing", 1)
        # Should return the high-end model (under 90% budget)
        assert model == "openai/gpt-4o"
        
        # Mock db_session for exceeded case (over 90%)
        mock_result2 = MagicMock()
        mock_scalars2 = MagicMock()
        
        # Create mock CostRecord objects
        mock_record2 = MagicMock()
        mock_record2.total_tokens = 19000
        mock_record2.est_cost_usd = 950.0  # 95% of budget
        mock_record2.task_type = "writing"
        mock_record2.created_at = None
        
        mock_scalars2.all.return_value = [mock_record2]
        mock_result2.scalars.return_value = mock_scalars2
        mock_session.execute.return_value = mock_result2
        
        model = await guard.get_recommended_model_for_task_async(mock_session, "writing", 1)
        # Should return the low-cost model (over 90% budget)
        assert model == "openai/gpt-4o-mini"