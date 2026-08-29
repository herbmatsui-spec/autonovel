"""tests/unit/test_consistency_cache.py"""
from src.consistency.cache import get_cache
from src.consistency.findings import Finding
from src.consistency.checkers.base import CheckContext


def test_cache_hit_miss():
    cache = get_cache()
    cache.clear()
    ctx = CheckContext(book_id=1, branch_id=1)
    assert cache.get(ctx) is None

    findings = [Finding(category="x", description="y")]
    cache.set(ctx, findings)
    assert cache.get(ctx) == findings


def test_cache_ttl():
    cache = get_cache()
    cache.clear()
    ctx = CheckContext(book_id=2, branch_id=1)
    cache._cache[cache._make_key(ctx)] = (0, [Finding(category="x", description="old")])  # expired
    assert cache.get(ctx) is None


def test_cache_invalidate():
    cache = get_cache()
    cache.clear()
    ctx = CheckContext(book_id=3, branch_id=1)
    findings = [Finding(category="x", description="y")]
    cache.set(ctx, findings)
    cache.invalidate(ctx)
    assert cache.get(ctx) is None


def test_cache_clear():
    cache = get_cache()
    cache.clear()
    cache.set(CheckContext(book_id=1), [Finding(category="x", description="y")])
    cache.clear()
    assert cache.get(CheckContext(book_id=1)) is None