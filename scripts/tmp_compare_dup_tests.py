import hashlib
import os

pairs = [
    ("tests/unit/test_prompt_version_service.py", "tests/unit/services/test_prompt_version_service.py"),
    ("tests/unit/test_semantic_cache.py", "tests/unit/services/test_semantic_cache.py"),
    ("tests/unit/test_uow_repositories.py", "tests/unit/database/test_uow_repositories.py"),
    ("tests/unit/test_vector_store.py", "tests/unit/services/test_vector_store.py"),
]

for a, b in pairs:
    ea, eb = os.path.exists(a), os.path.exists(b)
    ha = hashlib.md5(open(a, "rb").read()).hexdigest() if ea else "N/A"
    hb = hashlib.md5(open(b, "rb").read()).hexdigest() if eb else "N/A"
    print(a, os.path.getsize(a) if ea else -1, ha[:8])
    print(b, os.path.getsize(b) if eb else -1, hb[:8])
    print("SAME" if ha == hb else "DIFF", "---")
