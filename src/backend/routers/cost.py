# ruff: noqa: B008
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from src.backend.auth import get_current_user
from src.backend.database import get_async_db
from src.backend.database.models import User, Book, CostLogModel
from src.backend.database.repositories import CostRepository
from src.backend.security.roles import RoleChecker, UserRole
router = APIRouter(
    prefix="/api/cost",
    tags=["cost"],
    dependencies=[Depends(get_current_user), Depends(RoleChecker([UserRole.ADMIN, UserRole.PRO]))],
)


@router.get("/summary")
async def get_cost_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
    all_users: bool = Query(False, description="管理者のみ: 全ユーザー集約を取得"),
):
    # Get the start of the current month
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)

    # Query the cost logs for the current month
    from sqlalchemy import select
    from sqlalchemy.sql import column
    
    # Build the query using select instead of query() for AsyncSession
    stmt = select(
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
        user_book_ids = select(Book.id).filter(Book.user_id == current_user.id).subquery()
        stmt = stmt.filter(CostLogModel.book_id.in_(user_book_ids))

    result = await db.execute(stmt)
    results = result.first()

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


@router.get("/budget/{book_id}")
async def get_budget_consumption_ratio(
    book_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """特定の書籍のリアルタイム予算消費率を取得する。"""
    # 書籍の存在確認とアクセス権限チェック
    from sqlalchemy import select
    book_result = await db.execute(select(Book).where(Book.id == book_id))
    book = book_result.scalar_one_or_none()
    
    if book is None:
        raise HTTPException(status_code=404, detail="Book not found")
    
    # 権限チェック: 管理者または書籍の所有者のみアクセス可能
    if current_user.role != "admin" and book.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # コストリポジトリを使用して実際の消費コストと予算を取得
    cost_repo = CostRepository(db)
    
    # 実際の消費コストを取得
    aggregate_result = await cost_repo.aggregate(book_id)
    total_cost_usd = aggregate_result["total_cost_usd"]
    
    # 予算を取得
    budget_usd = await cost_repo.get_budget(book_id)
    
    # 予算消費率を計算
    if budget_usd <= 0:
        ratio = 0.0
        budget_status = "no_budget"
    else:
        ratio = total_cost_usd / budget_usd
        if ratio < 0.7:
            budget_status = "normal"
        elif ratio < 0.9:
            budget_status = "warning"
        else:
            budget_status = "exceeded"
    
    return {
        "book_id": book_id,
        "total_cost_usd": round(total_cost_usd, 4),
        "budget_usd": round(budget_usd, 2),
        "consumption_ratio": round(ratio, 4),
        "consumption_percentage": round(ratio * 100, 2),
        "budget_status": budget_status,
    }
