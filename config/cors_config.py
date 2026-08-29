from typing import List
import os
import json

def get_allowed_origins() -> List[str]:
    """環境変数からCORS許可originリストを取得"""
    origins_env = os.getenv("CORS_ALLOWED_ORIGINS")
    if origins_env is None:
        return []   # デフォルトは空リスト。生産環境ではライフサイクルで検証するため必須とする
    # Attempt to parse JSON array first (e.g., '["http://example.com"]')
    try:
        parsed = json.loads(origins_env)
        if isinstance(parsed, list):
            return [o.strip() for o in parsed if isinstance(o, str) and o.strip()]
    except json.JSONDecodeError:
        pass
    # Fallback to comma‑separated string
    return [o.strip() for o in origins_env.split(",") if o.strip()]