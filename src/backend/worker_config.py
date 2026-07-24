import os

from huey import RedisHuey, SqliteHuey

from src.backend.redis_util import REDIS_URL, get_redis_client
from src.core.observability import get_structured_logger

logger = get_structured_logger("huey_config")

# Dynamically decide the Huey backend based on Redis availability
redis_client = get_redis_client()
if redis_client is not None:
    huey = RedisHuey('kaku_hegemony', url=REDIS_URL)
    logger.info("Huey connected to Redis (backend=redis)")
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'storage', 'db', 'kaku_hegemony_v2_huey.db')
    huey = SqliteHuey(filename=DB_PATH)
    
    # Apply SQLite pragmas via helper function
    from .huey_config import apply_sqlite_pragmas
    apply_sqlite_pragmas(DB_PATH)
    
    logger.info(f"Huey falling back to SQLite backend (backend=sqlite, path={DB_PATH}, fallback_reason=redis_unavailable)")