#!/usr/bin/env python3
"""
シークレット検出スクリプト
pre-commit フックから呼び出される
"""
import sys
import re


def main() -> int:
    patterns = [
        r'api[_-]?key\s*[=:]\s*["\'][^"\']+["\']',
        r'secret[_-]?key\s*[=:]\s*["\'][^"\']+["\']',
        r'password\s*[=:]\s*["\'][^"\']+["\']',
        r'token\s*[=:]\s*["\'][^"\']+["\']',
    ]

    for f in sys.argv[1:]:
        try:
            content = open(f).read()
        except (OSError, UnicodeDecodeError):
            continue

        for i, line in enumerate(content.splitlines(), 1):
            for p in patterns:
                if re.search(p, line, re.IGNORECASE):
                    print(f'{f}:{i}: Potential secret found: {line.strip()[:80]}')
                    return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())