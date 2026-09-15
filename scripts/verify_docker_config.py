#!/usr/bin/env python3
"""Docker設定とヘルスチェック構成の自動検証スクリプト。"""
import sys
from pathlib import Path


def main() -> int:
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")

    errors = []
    if "AS builder" not in dockerfile or "AS runner" not in dockerfile:
        errors.append("Dockerfile is not multi-stage (missing 'AS builder' or 'AS runner').")

    if "USER appuser" not in dockerfile:
        errors.append("Dockerfile does not run as non-root user 'appuser'.")

    if "health/liveness" not in compose and "health" not in compose:
        errors.append("docker-compose.yml does not define a valid healthcheck endpoint.")

    if errors:
        print("[FAIL] Docker configuration issues found:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("[SUCCESS] Docker multi-stage build and healthcheck configuration are valid!")
    return 0


if __name__ == "__main__":
    sys.exit(main())