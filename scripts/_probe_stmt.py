"""一時検証スクリプト: SQLAlchemy select の compile 結果確認。"""
import sys

sys.path.insert(0, "e:/hhh")

from sqlalchemy import select  # noqa: E402
from src.backend.database.models import Plot  # noqa: E402

s = select(Plot).where(Plot.book_id == 1, Plot.ep_num == 1)
compiled = str(s)
print(repr(compiled[:300]))
print("plots in compiled:", "plots" in compiled.lower())
