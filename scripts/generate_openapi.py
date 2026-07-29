#!/usr/bin/env python3
"""OpenAPI 仕様書を JSON としてエクスポートする補助スクリプト (Step 59)。

使い方:
    py scripts/generate_openapi.py
    py scripts/generate_openapi.py --output custom_path/openapi.json

FastAPI アプリから app.openapi() を取得し、docs/openapi.json へ保存する。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AutoNovel FastAPI の OpenAPI 仕様書を JSON 出力する"
    )
    parser.add_argument(
        "--output",
        "-o",
        default="docs/openapi.json",
        help="出力先ファイルパス (既定: docs/openapi.json)",
    )
    args = parser.parse_args()

    # conftest が sys.path を修正する前提だが、スクリプト単独動作を担保する。
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # 遅延 import により sys.path 挿入を反映
    from src.backend.server import app  # noqa: PLC0415

    openapi_spec = app.openapi()
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(openapi_spec, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"OpenAPI 仕様書を書き出しました: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
