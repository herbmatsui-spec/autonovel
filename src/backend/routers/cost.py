# ruff: noqa: B008
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.backend.auth import get_current_user
from src.backend.database import get_db
from src.backend.database.models import User, Book, CostLogModel
from src.backend.security.roles import RoleChecker, UserRole

router = APIRouter(
    prefix="/api/cost",
    tags=["cost"],
    dependencies=[Depends(get_current_user), Depends(RoleChecker([UserRole.ADMIN, UserRole.PRO]))],
)

@router.get("/summary")
async def get_cost_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    all_users: bool = Query(False, description="管理者のみ: 全ユーザー集約を取得"),
):
    # Get the start of the current month
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)

    # Query the cost logs for the current month
    query = db.query(
        func.sum(CostLogModel.cost_usd).label("total_cost_usd"),
        func.sum(CostLogModel.input_tokens).label("total_input_tokens"),
        func.sum(CostLogModel.output_tokens).label("total_output_tokens"),
        func.sum(getattr(CostLogModel, "cache_read_tokens", 0)).label("total_cache_read_tokens") if hasattr(CostLogModel, "cache_read_tokens") else func.sum(0).label("total_cache_read_tokens"),
        func.sum(getattr(CostLogModel, "cache_creation_tokens", 0)).label("total_cache_creation_tokens") if hasattr(CostLogModel, "cache_creation_tokens") else func.sum(0).label("total_cache_creation_tokens"),
    ).filter(
        CostLogModel.timestamp >= start_of_month
    )

    # 一般ユーザー、または管理者でall_users=Falseの場合は自身が所有する書籍に限定
    if current_user.role != "admin" or not all_users:
        user_book_ids = db.query(Book.id).filter(Book.user_id == current_user.id).subquery()
        query = query.filter(CostLogModel.book_id.in_(user_book_ids))

    results = query.first()

    total_cost_usd = results.total_cost_usd or 0.0
    total_input_tokens = results.total_input_tokens or 0
    total_output_tokens = results.total_output_tokens or 0
    total_cache_read = results.total_cache_read_tokens or 0

    # Calculate total tokens (input + output) for cache hit ratio
    total_tokens = total_input_tokens + total_output_tokens
    cache_hit_ratio = 0.0
    if total_tokens > 0:
        # Cache hit ratio: cache_read_tokens / (input_tokens + cache_read_tokens)
        # We don't have a direct field for cache hits in input, but we can approximate
        # We'll use: cache_read_tokens / (input_tokens + cache_read_tokens) if input_tokens + cache_read_tokens > 0
        if total_input_tokens + total_cache_read > 0:
            cache_hit_ratio = total_cache_read / (total_input_tokens + total_cache_read)
        else:
            cache_hit_ratio = 0.0

    # Convert cost to JPY (assuming 150 JPY per USD)
    total_cost_jpy = total_cost_usd * 150.0

    # Calculate savings from cache (assuming cached input costs 0.025 per 1M tokens vs 0.10 for flash)
    # This is a simplification; in reality, we would use the actual model pricing.
    # We'll assume the base model is gemini-2.0-flash for input pricing.
    base_input_price_per_1m = 0.10  # USD per 1M input tokens
    cached_input_price_per_1m = 0.025  # USD per 1M cached input tokens
    savings_usd = (total_cache_read / 1_000_000) * (base_input_price_per_1m - cached_input_price_per_1m)
    savings_jpy = savings_usd * 150.0

    return {
        "total_cost_jpy": round(total_cost_jpy, 2),
        "total_cost_usd": round(total_cost_usd, 2),
        "cache_hit_ratio": round(cache_hit_ratio, 4),
        "savings_jpy": round(savings_jpy, 2),
        "savings_usd": round(savings_usd, 2),
    }
