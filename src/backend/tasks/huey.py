"""Huey タスクキュー設定。環境変数で sqlite/redis を切り替える。"""
from __future__ import annotations

import logging
import os

from huey import RedisHuey, SqliteHuey

logger = logging.getLogger(__name__)

huey_backend = os.getenv("HUEY_BACKEND", "sqlite")
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

if huey_backend == "redis":
    huey = RedisHuey("autonovel", url=redis_url)
else:
    huey = SqliteHuey("autonovel")

# ワーカー上で即時実行せず、キュー経由で実行する
huey.immediate = False


# ワーカー側でタスクを認識するためにここでインポートしておく
import src.backend.tasks.generation_tasks  # noqa

__all__: list[str] = ["huey", "logger"]
