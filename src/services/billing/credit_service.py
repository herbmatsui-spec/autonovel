import logging
from typing import Optional
from sqlalchemy import select, update
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
        auto_commit: bool = True,
    ) -> int:
        """クレジットをアトミックに加算付与し、台帳に記録する。"""
        if amount <= 0:
            raise ValueError(f"付与額は正の整数である必要があります: {amount}")

        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(credits=User.credits + amount)
        )
        result = await self.db.execute(stmt)
        if result.rowcount == 0:
            raise ValueError(f"ユーザーが見つかりません: {user_id}")

        new_balance = await self.get_balance(user_id)

        transaction = CreditTransaction(
            user_id=user_id,
            amount=amount,
            balance_after=new_balance,
            transaction_type=transaction_type,
            task_id=task_id,
            description=description,
        )
        self.db.add(transaction)
        if auto_commit:
            await self.db.commit()
            await self.db.refresh(transaction)
        else:
            await self.db.flush()
        return new_balance

    async def deduct_credits(
        self,
        user_id: int,
        amount: int,
        transaction_type: str,
        description: str,
        task_id: Optional[str] = None,
        auto_commit: bool = True,
    ) -> bool:
        """クレジットをアトミックに厳格減算し、二重消費や競合を防止する。
        残高不足時は InsufficientCreditsError を送出。
        """
        if amount < 0:
            raise ValueError(f"消費額は0以上である必要があります: {amount}")
        if amount == 0:
            return True

        # アトミック UPDATE (SQLite/PostgreSQL 共通対応)
        # credits >= amount の条件により、同時リクエスト時も残高不足でのマイナス消費をDBレベルで防ぐ
        stmt = (
            update(User)
            .where(User.id == user_id, User.credits >= amount)
            .values(credits=User.credits - amount)
        )
        result = await self.db.execute(stmt)

        if result.rowcount == 0:
            # ユーザー不在か残高不足かを判定
            user_exists = (
                await self.db.execute(select(User.id).where(User.id == user_id))
            ).scalar_one_or_none()
            if not user_exists:
                raise ValueError(f"ユーザーが見つかりません: {user_id}")

            current_balance = await self.get_balance(user_id)
            raise InsufficientCreditsError(
                f"Insufficient credits. Required: {amount}, Available: {current_balance}"
            )

        new_balance = await self.get_balance(user_id)

        transaction = CreditTransaction(
            user_id=user_id,
            amount=-amount,
            balance_after=new_balance,
            transaction_type=transaction_type,
            task_id=task_id,
            description=description,
        )
        self.db.add(transaction)
        if auto_commit:
            await self.db.commit()
            await self.db.refresh(transaction)
        else:
            await self.db.flush()
        return True
