import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession

from src.backend.routers.cost import get_budget_consumption_ratio, get_cost_summary
from src.backend.database.models import User, Book
from fastapi import HTTPException


@pytest.mark.asyncio
async def test_get_budget_consumption_ratio_success():
    """正常な予算消費率取得のテスト"""
    # Mock dependencies
    mock_db = AsyncMock(spec=AsyncSession)
    mock_current_user = MagicMock(spec=User)
    mock_current_user.id = 1
    mock_current_user.role = "user"
    
    # Mock book query result
    mock_book = MagicMock(spec=Book)
    mock_book.id = 1
    mock_book.user_id = 1  # Same as current_user.id
    
    # Mock the book query execution
    mock_book_result = MagicMock()
    mock_book_result.scalar_one_or_none.return_value = mock_book
    mock_db.execute.return_value = mock_book_result
    
    # Mock CostRepository
    with patch('src.backend.routers.cost.CostRepository') as mock_repo_class:
        mock_repo_instance = AsyncMock()
        mock_repo_class.return_value = mock_repo_instance
        
        # Mock aggregate result (cost = 7.5 USD)
        mock_repo_instance.aggregate.return_value = {
            "total_cost_usd": 7.5,
            "total_tokens": 1500,
            "record_count": 15,
            "by_task": {},
            "timeseries": []
        }
        
        # Mock get_budget result (budget = 10.0 USD)
        mock_repo_instance.get_budget.return_value = 10.0
        
        # Call the function
        result = await get_budget_consumption_ratio(
            book_id=1,
            current_user=mock_current_user,
            db=mock_db
        )
        
        # Assertions
        assert result["book_id"] == 1
        assert result["total_cost_usd"] == 7.5
        assert result["budget_usd"] == 10.0
        assert result["consumption_ratio"] == 0.75  # 7.5 / 10.0
        assert result["consumption_percentage"] == 75.0
        assert result["budget_status"] == "warning"  # 70-90% range


@pytest.mark.asyncio
async def test_get_budget_consumption_ratio_book_not_found():
    """存在しない書籍IDのテスト"""
    # Mock dependencies
    mock_db = AsyncMock(spec=AsyncSession)
    mock_current_user = MagicMock(spec=User)
    mock_current_user.id = 1
    mock_current_user.role = "user"
    
    # Mock book query result (not found)
    mock_book_result = MagicMock()
    mock_book_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_book_result
    
    # Call the function and expect exception
    with pytest.raises(HTTPException) as exc_info:
        await get_budget_consumption_ratio(
            book_id=999,
            current_user=mock_current_user,
            db=mock_db
        )
    
    assert exc_info.value.status_code == 404
    assert "Book not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_budget_consumption_ratio_access_denied():
    """アクセス権限がない場合のテスト"""
    # Mock dependencies
    mock_db = AsyncMock(spec=AsyncSession)
    mock_current_user = MagicMock(spec=User)
    mock_current_user.id = 1  # Current user ID
    mock_current_user.role = "user"
    
    # Mock book query result (book belongs to different user)
    mock_book = MagicMock(spec=Book)
    mock_book.id = 1
    mock_book.user_id = 2  # Different from current_user.id
    
    # Mock the book query execution
    mock_book_result = MagicMock()
    mock_book_result.scalar_one_or_none.return_value = mock_book
    mock_db.execute.return_value = mock_book_result
    
    # Call the function and expect exception
    with pytest.raises(HTTPException) as exc_info:
        await get_budget_consumption_ratio(
            book_id=1,
            current_user=mock_current_user,
            db=mock_db
        )
    
    assert exc_info.value.status_code == 403
    assert "Access denied" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_get_budget_consumption_ratio_no_budget():
    """予算が設定されていない場合のテスト"""
    # Mock dependencies
    mock_db = AsyncMock(spec=AsyncSession)
    mock_current_user = MagicMock(spec=User)
    mock_current_user.id = 1
    mock_current_user.role = "user"
    
    # Mock book query result
    mock_book = MagicMock(spec=Book)
    mock_book.id = 1
    mock_book.user_id = 1
    
    # Mock the book query execution
    mock_book_result = MagicMock()
    mock_book_result.scalar_one_or_none.return_value = mock_book
    mock_db.execute.return_value = mock_book_result
    
    # Mock CostRepository
    with patch('src.backend.routers.cost.CostRepository') as mock_repo_class:
        mock_repo_instance = AsyncMock()
        mock_repo_class.return_value = mock_repo_instance
        
        # Mock aggregate result (cost = 5.0 USD)
        mock_repo_instance.aggregate.return_value = {
            "total_cost_usd": 5.0,
            "total_tokens": 1000,
            "record_count": 10,
            "by_task": {},
            "timeseries": []
        }
        
        # Mock get_budget result (budget = 0.0 USD - no budget set)
        mock_repo_instance.get_budget.return_value = 0.0
        
        # Call the function
        result = await get_budget_consumption_ratio(
            book_id=1,
            current_user=mock_current_user,
            db=mock_db
        )
        
        # Assertions
        assert result["book_id"] == 1
        assert result["total_cost_usd"] == 5.0
        assert result["budget_usd"] == 0.0
        assert result["consumption_ratio"] == 0.0
        assert result["consumption_percentage"] == 0.0
        assert result["budget_status"] == "no_budget"


# Import patch at the top to avoid issues
from unittest.mock import patch