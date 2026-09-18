"""一時検証スクリプト: _fetch_plot の挙動確認。"""
import sys

sys.path.insert(0, "e:/hhh")

from unittest.mock import MagicMock, AsyncMock  # noqa: E402

from src.services.book_score_service import BookScoreCalculator  # noqa: E402
from src.backend.database.models import Plot  # noqa: E402
from sqlalchemy import select  # noqa: E402

calc = BookScoreCalculator.__new__(BookScoreCalculator)
calc._repository = MagicMock()
calc._repository.session = MagicMock()


def execute(stmt, *args, **kwargs):
    try:
        compiled = str(stmt.compile()).lower()
        print("compile ok:", compiled[:60])
    except Exception as e:
        print("compile failed:", type(e).__name__, e)
        compiled = str(stmt).lower()
    result = MagicMock()
    scalars = MagicMock()
    scalars.first.return_value = MagicMock(end_ep=5)
    result.scalars.return_value = scalars
    return result


session = MagicMock()
session.execute = AsyncMock(side_effect=execute)
calc._repository.session = session

import asyncio  # noqa: E402

plot = asyncio.run(calc._fetch_plot(1, 1))
print("plot:", plot)
