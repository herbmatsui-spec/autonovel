"""
OpenAPIスキーマをJSON形式で出力するスクリプト
"""
import json
import sys
import os

# プロジェクトのルートディレクトリを sys.path に追加してモジュールを見つけられるようにする
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.backend.server import app

def main():
    schema = app.openapi()
    os.makedirs("docs", exist_ok=True)
    with open("docs/openapi.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    print("docs/openapi.json にOpenAPIスキーマを出力しました")

if __name__ == "__main__":
    main()
