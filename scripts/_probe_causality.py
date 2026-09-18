"""一時検証スクリプト: DomainProfileService.get_default_causality_map 確認。"""
import sys

sys.path.insert(0, "e:/hhh")

try:
    from config.domain_profile_manager import DomainProfileService  # noqa: E402
except ImportError:
    from src.config.domain_profile_manager import DomainProfileService  # type: ignore  # noqa: E402

import inspect  # noqa: E402

m = DomainProfileService.get_default_causality_map
print("signature:", inspect.signature(m))
r = m("fantasy", "default")
print("type:", type(r).__name__)
print("value:", str(r)[:150])
