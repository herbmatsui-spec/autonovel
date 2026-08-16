import asyncio

import pytest

from src.core.rate_limiter import TokenBucket


@pytest.mark.asyncio
async def test_token_bucket_initial_full():
    bucket = TokenBucket(capacity=2.0, fill_rate=1.0)
    assert await bucket.consume(1.0) is True
    assert await bucket.consume(1.0) is True
    assert await bucket.consume(1.0) is False


@pytest.mark.asyncio
async def test_token_bucket_refills():
    bucket = TokenBucket(capacity=1.0, fill_rate=10.0)
    assert await bucket.consume(1.0) is True
    assert await bucket.consume(1.0) is False
    await asyncio.sleep(0.2)
    # 10 tokens/sec * 0.2s ~= 2 tokens 溜まるので再消費可能
    assert await bucket.consume(1.0) is True


@pytest.mark.asyncio
async def test_token_bucket_over_capacity_rejected():
    bucket = TokenBucket(capacity=1.0, fill_rate=1.0)
    # 容量を超える要求は即座に拒否
    assert await bucket.consume(5.0) is False
