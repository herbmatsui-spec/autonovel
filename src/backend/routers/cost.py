from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from src.backend.database import get_db
from src.backend.database.models import CostLogModel
from sqlalchemy import func
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/cost", tags=["cost"])

@router.get("/summary")
async def get_cost_summary(db: Session = Depends(get_db)):
    # Get the start of the current month
    now = datetime.now()
    start_of_month = datetime(now.year, now.month, 1)
    
    # Query the cost logs for the current month
    results = db.query(
        func.sum(CostLogModel.cost_usd).label("total_cost_usd"),
        func.sum(CostLogModel.input_tokens).label("total_input_tokens"),
        func.sum(CostLogModel.output_tokens).label("total_output_tokens"),
        func.sum(CostLogModel.cache_read_tokens).label("total_cache_read_tokens"),
        func.sum(CostLogModel.cache_creation_tokens).label("total_cache_creation_tokens")
    ).filter(
        CostLogModel.timestamp >= start_of_month
    ).first()
    
    total_cost_usd = results.total_cost_usd or 0.0
    total_input_tokens = results.total_input_tokens or 0
    total_output_tokens = results.total_output_tokens or 0
    total_cache_read = results.total_cache_read_tokens or 0
    total_cache_creation = results.total_cache_creation_tokens or 0
    
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
