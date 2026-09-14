import logging
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.database.models_billing import CreditTransaction
from src.backend.database.models import User

logger = logging.getLogger(__name__)

class InsufficientCreditsError(Exception):
    """Raised when user attempts to deduct more credits than available."""
    pass

class CreditService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_balance(self, user_id: int) -> int:
        """ユーザーの現在のクレジット残高を取得する (users.credits を絶対マスターとする)。"""
        query = select(User.credits).where(User.id == user_id)
        result = await self.db.execute(query)
        balance = result.scalar_one_or_none()
        if balance is None:
            return 0
        return balance

    async def grant_credits(
        self,
        user_id: int,
        amount: int,
        transaction_type: str,
        description: str,
        task_id: Optional[str] = None,
    ) -> int:
        """クレジットを行ロック下で安全に付与し、台帳に同一トランザクションで記録する。"""
        if amount <= 0:
            raise ValueError(f"付与額は正の整数である必要があります: {amount}")

        stmt = select(User).where(User.id == user_id).with_for_update()
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"ユーザーが見つかりません: {user_id}")

        user.credits += amount
        new_balance = user.credits

        transaction = CreditTransaction(
            user_id=user_id,
            amount=amount,
            balance_after=new_balance,
            transaction_type=transaction_type,
            task_id=task_id,
            description=description,
        )
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        return new_balance

    async def deduct_credits(
        self,
        user_id: int,
        amount: int,
        transaction_type: str,
        description: str,
        task_id: Optional[str] = None,
    ) -> bool:
        """クレジットを行ロック下で厳格に減算し、二重消費を防止する。
        残高不足時は InsufficientCreditsError を送出。
        """
        if amount < 0:
            raise ValueError(f"消費額は0以上である必要があります: {amount}")
        if amount == 0:
            return True

        stmt = select(User).where(User.id == user_id).with_for_update()
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError(f"ユーザーが見つかりません: {user_id}")

        if user.credits < amount:
            raise InsufficientCreditsError(
                f"Insufficient credits. Required: {amount}, Available: {user.credits}"
            )

        user.credits -= amount
        new_balance = user.credits

        transaction = CreditTransaction(
            user_id=user_id,
            amount=-amount,
            balance_after=new_balance,
            transaction_type=transaction_type,
            task_id=task_id,
            description=description,
        )
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        return True