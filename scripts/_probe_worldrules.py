"""一時検証スクリプト: WorldRules の causality_map 型確認。"""
import sys

sys.path.insert(0, "e:/hhh")

from src.models.bible import WorldRules  # noqa: E402

r = WorldRules()
print("causality_map type:", type(r.causality_map).__name__)
print("value:", r.causality_map)
