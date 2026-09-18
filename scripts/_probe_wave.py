"""一時検証スクリプト: WavePatternAnalyzer の挙動確認（実行後削除可）。"""
import sys

sys.path.insert(0, "e:/hhh")

from src.backend.engine_narrative import WavePatternAnalyzer  # noqa: E402

a = WavePatternAnalyzer(threshold=65, reset_value=0)
r = a.analyze([80, 30])
print("pattern:", r.model_dump())
r2 = a.analyze([50] * 5)
print("flat:", r2.model_dump())
