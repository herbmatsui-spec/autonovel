#!/usr/bin/env python3
"""
Check for potential secrets in code.
"""
import sys
import re
from pathlib import Path


def check_file(filepath: Path) -> list:
    """Check a file for potential secrets."""
    errors = []
    patterns = [
        r'api[_-]?key\s*[=:]\s*["\'][^"\']+["\']',
        r'secret[_-]key\s*[=:]\s*["\'][^"\']+["\']',
        r'password\s*[=:]\s*["\'][^"\']+["\']',
        r'token\s*[=:]\s*["\'][^"\']+["\']',
    ]
    try:
        content = filepath.read_text(encoding="utf-8")
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            # Skip comments
            if stripped.startswith("#"):
                continue
            for p in patterns:
                if re.search(p, line, re.IGNORECASE):
                    errors.append(f"{filepath}:{i}: Potential secret found: {stripped[:80]}")
    except Exception as e:
        errors.append(f"{filepath}: Error reading file: {e}")
    return errors


def find_files(path: Path) -> list:
    """Find all relevant files in a path recursively."""
    if path.is_file():
        return [path] if path.suffix in {".py", ".toml", ".yaml", ".yml", ".env"} else []
    files = []
    for f in path.rglob("*"):
        if f.is_file() and f.suffix in {".py", ".toml", ".yaml", ".yml", ".env"}:
            files.append(f)
    return files


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: no_secret_check.py <file1> [file2] ...")
        sys.exit(1)

    # Directories to exclude
    exclude_dirs = {"tests", "scripts", "docs", "alembic"}

    all_errors = []
    for arg in sys.argv[1:]:
        filepath = Path(arg)
        # Find all relevant files
        target_files = find_files(filepath)
        for f in target_files:
            # Skip excluded directories
            if any(part in exclude_dirs for part in f.parts):
                continue
            errors = check_file(f)
            all_errors.extend(errors)

    if all_errors:
        for error in all_errors:
            print(error)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()