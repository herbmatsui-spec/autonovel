import os
from typing import List

def get_allowed_origins() -> List[str]:
    """環境変数からCORS許可originリストを取得"""
    origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
    if not origins_env:
        # デフォルトは開発用
        return ["http://localhost:5173", "http://localhost:8501"]
    return [o.strip() for o in origins_env.split(",") if o.strip()]