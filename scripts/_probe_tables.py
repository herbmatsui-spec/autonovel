"""一時検証スクリプト: Plot/Chapter/Bible/Illustration モデルのテーブル名確認。"""
import sys

sys.path.insert(0, "e:/hhh")
from src.backend.database.models import (  # noqa: E402
    AuditIssue,
    Bible,
    Chapter,
    Illustration,
    Plot,
)

for m in (Plot, Chapter, Bible, Illustration, AuditIssue):
    print(m.__name__, "->", m.__tablename__)
