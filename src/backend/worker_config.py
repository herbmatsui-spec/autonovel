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
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kaku_hegemony_v2_huey.db')
    huey = SqliteHuey(filename=DB_PATH)

    # HueyのSQLite接続に対してWALモードとTimeoutを強制適用する
    try:
        import sqlite3
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        conn.execute("PRAGMA busy_timeout=30000;")
        conn.close()
        logger.info(f"WAL mode and timeout applied to Huey DB: {DB_PATH}")
    except Exception as e:
        logger.error(f"Failed to apply SQLite PRAGMAs to Huey DB: {e}")

    logger.info(f"Huey falling back to SQLite backend (backend=sqlite, path={DB_PATH})")


