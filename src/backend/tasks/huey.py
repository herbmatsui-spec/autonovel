"""Huey タスクキュー設定。環境変数で sqlite/redis を切り替える。"""

from __future__ import annotations

import logging

from huey import RedisHuey, SqliteHuey

from src.backend.config import settings

logger = logging.getLogger(__name__)

if settings.HUEY_BACKEND == "redis":
    huey = RedisHuey("autonovel", url=settings.REDIS_URL)
else:
    huey = SqliteHuey("autonovel", filename=settings.HUEY_SQLITE_PATH)

# ワーカー上で即時実行せず、キュー経由で実行する
huey.immediate = False


# ワーカー側でタスクを認識するためにここでインポートしておく
import src.backend.tasks  # noqa
import src.backend.tasks.generation_tasks  # noqa

__all__: list[str] = ["huey", "logger"]
