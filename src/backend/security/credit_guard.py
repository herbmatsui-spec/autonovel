from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from src.backend.database import get_db
from src.backend.auth import get_current_user
from src.backend.database.models import User
from src.config.billing_plans import TASK_CREDIT_COSTS

def require_credits(task_type: str):
    """Dependency that verifies user has sufficient credits for a task type."""
    async def dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ):
        # Get required credits for the task type
        required = TASK_CREDIT_COSTS.get(task_type, 10)  # Default to 10 if not found
        
        # Check if user has sufficient credits
        if current_user.credits < required:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error_code": "INSUFFICIENT_CREDITS",
                    "required": required,
                    "balance": current_user.credits
                }
            )
        return required
    return dependency