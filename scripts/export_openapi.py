"""FastAPI アプリケーションから openapi.json をエクスポートするスクリプト。"""
import json
import os
import sys
from pathlib import Path

# ルートディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.backend.server import app

def export_openapi():
    output_path = Path("docs/openapi.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    openapi_schema = app.openapi()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"OpenAPI schema successfully exported to: {output_path}")

if __name__ == "__main__":
    export_openapi()
