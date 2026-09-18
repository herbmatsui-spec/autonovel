"""一時検証スクリプト: system.py の import 先確認。"""
import sys

sys.path.insert(0, "e:/hhh")

for mod_name in ("src.infrastructure.database.models.book",
                 "src.infrastructure.database.models.book_score",
                 "src.infrastructure.database.models.chapter",
                 "src.backend.database.models",
                 "src.backend.database.repositories.book_score"):
    try:
        __import__(mod_name)
        print("OK:", mod_name)
    except ModuleNotFoundError as e:
        print("MISSING:", mod_name, "->", e.name)
