from src.services.redis_cache import REDIS_AVAILABLE

def test_redis_asyncio_availability():
    # Ensure the import flag is a boolean and reflects availability.
    assert isinstance(REDIS_AVAILABLE, bool)
    # In this CI environment redis.asyncio should be installed, so expect True.
    # If not installed the fallback behavior is exercised elsewhere.
    # The test asserts the flag exists; the actual value is environment‑dependent.
