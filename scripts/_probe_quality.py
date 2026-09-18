"""一時検証スクリプト: QualityMetrics の overall_quality 確認。"""
import sys

sys.path.insert(0, "e:/hhh")

from src.backend.workflows.quality_metrics import QualityMetrics  # noqa: E402
import time  # noqa: E402

m = QualityMetrics(ep_num=1, integrity_ok=True, causal_ok=True, rate=0.5,
                   ac_iter=0, threshold=0, timestamp=time.time(),
                   genre="fantasy", dogfeed_ok=True, causal_reason="")
print("overall_quality:", m.overall_quality)

m2 = QualityMetrics(ep_num=2, integrity_ok=False, causal_ok=False, rate=0.2,
                    ac_iter=0, threshold=0, timestamp=time.time(),
                    genre="fantasy", dogfeed_ok=False, causal_reason="")
print("low quality:", m2.overall_quality)
