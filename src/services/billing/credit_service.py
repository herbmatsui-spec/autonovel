from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.database.models_billing import CreditTransaction
from src.backend.database.models import User
from typing import Optional

class InsufficientCreditsError(Exception):
    """Raised when user attempts to deduct more credits than available."""
    pass

class CreditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_balance(self, user_id: int) -> int:
        """Get current credit balance for a user."""
        # Get the most recent transaction to determine current balance
        query = select(CreditTransaction.balance_after).where(
            CreditTransaction.user_id == user_id
        ).order_by(CreditTransaction.created_at.desc(), CreditTransaction.id.desc()).limit(1)
        
        result = await self.db.execute(query)
        balance = result.scalar_one_or_none()
        
        # If no transactions found, user likely has default balance from users table
        if balance is None:
            # Get default credits from users table
            user_query = select(User.credits).where(User.id == user_id)
            user_result = await self.db.execute(user_query)
            balance = user_result.scalar_one_or_none() or 0
            
        return balance

    async def grant_credits(self, user_id: int, amount: int, transaction_type: str, description: str, task_id: Optional[str] = None) -> int:
        """Grant credits to a user and record the transaction."""
        current_balance = await self.get_balance(user_id)
        new_balance = current_balance + amount
        
        # Create transaction record
        transaction = CreditTransaction(
            user_id=user_id,
            amount=amount,  # Positive for granting
            balance_after=new_balance,
            transaction_type=transaction_type,
            task_id=task_id,
            description=description
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        return new_balance

    async def deduct_credits(self, user_id: int, amount: int, transaction_type: str, description: str, task_id: Optional[str] = None) -> bool:
        """Deduct credits from a user if sufficient balance exists.
        
        Returns True if deduction was successful, False if insufficient funds.
        """
        current_balance = await self.get_balance(user_id)
        
        if current_balance < amount:
            raise InsufficientCreditsError(
                f"Insufficient credits. Required: {amount}, Available: {current_balance}"
            )
        
        new_balance = current_balance - amount
        
        # Create transaction record
        transaction = CreditTransaction(
            user_id=user_id,
            amount=-amount,  # Negative for deduction
            balance_after=new_balance,
            transaction_type=transaction_type,
            task_id=task_id,
            description=description
        )
        
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        
        return True