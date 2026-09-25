"""クレジット減算のテスト: 残高不足・二重消費防止"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.billing.credit_service import CreditService, InsufficientCreditsError


@pytest.mark.asyncio
async def test_insufficient_credits_raises_error():
    """残高不足時に InsufficientCreditsError が発生し、残高がマイナスにならないことをテスト"""
    mock_session = AsyncMock(spec=AsyncSession)
    
    mock_update_result = MagicMock()
    mock_update_result.rowcount = 0
    
    mock_select_result = MagicMock()
    mock_select_result.scalar_one_or_none.return_value = 1  # user exists
    
    mock_session.execute.side_effect = [
        mock_update_result,   # First call: UPDATE
        mock_select_result,   # Second call: SELECT User.id
    ]
    
    credit_service = CreditService(mock_session)
    
    async def mock_get_balance(user_id):
        return 5
    
    credit_service.get_balance = mock_get_balance
    
    with pytest.raises(InsufficientCreditsError) as exc_info:
        await credit_service.deduct_credits(
            user_id=1,
            amount=10,
            transaction_type="test",
            description="Test deduction"
        )
    
    assert "Insufficient credits" in str(exc_info.value)
    assert "Required: 10" in str(exc_info.value)
    assert "Available: 5" in str(exc_info.value)


@pytest.mark.asyncio
async def test_user_not_found_raises_error():
    """存在しないユーザーでエラーになる"""
    mock_session = AsyncMock(spec=AsyncSession)
    
    mock_update_result = MagicMock()
    mock_update_result.rowcount = 0
    
    mock_select_result = MagicMock()
    mock_select_result.scalar_one_or_none.return_value = None  # user not found
    
    mock_session.execute.side_effect = [
        mock_update_result,
        mock_select_result,
    ]
    
    credit_service = CreditService(mock_session)
    
    with pytest.raises(ValueError) as exc_info:
        await credit_service.deduct_credits(
            user_id=999,
            amount=5,
            transaction_type="test",
            description="User not found"
        )
    
    assert "ユーザーが見つかりません" in str(exc_info.value)


@pytest.mark.asyncio
async def test_zero_amount_deduction():
    """消費額0の場合はTrueを返す（エラーにしない）"""
    mock_session = AsyncMock(spec=AsyncSession)
    credit_service = CreditService(mock_session)
    
    result = await credit_service.deduct_credits(
        user_id=1,
        amount=0,
        transaction_type="test",
        description="Zero deduction"
    )
    
    assert result is True
    mock_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_negative_amount_raises_error():
    """負の消費額はエラーになる"""
    mock_session = AsyncMock(spec=AsyncSession)
    credit_service = CreditService(mock_session)
    
    with pytest.raises(ValueError) as exc_info:
        await credit_service.deduct_credits(
            user_id=1,
            amount=-5,
            transaction_type="test",
            description="Negative deduction"
        )
    
    assert "消費額は0以上である必要があります" in str(exc_info.value)


@pytest.mark.asyncio
async def test_deduct_credits_for_text_writing():
    """テキスト執筆用クレジット消費メソッドのテスト - 定数 COST_PER_EPISODE が使用されることを確認"""
    mock_session = AsyncMock(spec=AsyncSession)
    
    mock_update_result = MagicMock()
    mock_update_result.rowcount = 1
    
    mock_balance_result = MagicMock()
    mock_balance_result.scalar_one_or_none.return_value = 9
    
    mock_session.execute.side_effect = [
        mock_update_result,      # UPDATE
        mock_balance_result,     # get_balance (first)
        mock_balance_result,     # get_balance (second after transaction)
    ]
    
    async def mock_get_balance(user_id):
        return 9
    
    credit_service = CreditService(mock_session)
    credit_service.get_balance = mock_get_balance
    
    result = await credit_service.deduct_credits_for_text_writing(user_id=1)
    
    assert result is True


@pytest.mark.asyncio
async def test_deduct_credits_for_illustration():
    """画像生成用クレジット消費メソッドのテスト - 定数 COST_PER_ILLUSTRATION が使用されることを確認"""
    mock_session = AsyncMock(spec=AsyncSession)
    
    mock_update_result = MagicMock()
    mock_update_result.rowcount = 1
    
    mock_balance_result = MagicMock()
    mock_balance_result.scalar_one_or_none.return_value = 5
    
    mock_session.execute.side_effect = [
        mock_update_result,
        mock_balance_result,
        mock_balance_result,
    ]
    
    async def mock_get_balance(user_id):
        return 5
    
    credit_service = CreditService(mock_session)
    credit_service.get_balance = mock_get_balance
    
    result = await credit_service.deduct_credits_for_illustration(user_id=1)
    
    assert result is True


@pytest.mark.asyncio
async def test_deduct_credits_success():
    """正常なクレジット減算フローのテスト"""
    mock_session = AsyncMock(spec=AsyncSession)
    
    mock_update_result = MagicMock()
    mock_update_result.rowcount = 1
    
    mock_balance_result = MagicMock()
    mock_balance_result.scalar_one_or_none.return_value = 5
    
    mock_session.execute.side_effect = [
        mock_update_result,      # UPDATE
        mock_balance_result,     # get_balance (first)
        mock_balance_result,     # get_balance (second after transaction)
    ]
    
    async def mock_get_balance(user_id):
        return 5
    
    credit_service = CreditService(mock_session)
    credit_service.get_balance = mock_get_balance
    
    result = await credit_service.deduct_credits(
        user_id=1,
        amount=5,
        transaction_type="consumption",
        description="Normal deduction"
    )
    
    assert result is True