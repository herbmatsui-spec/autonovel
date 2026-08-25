#!/usr/bin/env python3
"""
Check for print statements in production code (src/ directory).
Allows print in tests/, scripts/, docs/, alembic/ directories.
"""
import sys
import re
from pathlib import Path


def check_file(filepath: Path) -> list:
    """Check a Python file for print statements in production code."""
    errors = []
    try:
        content = filepath.read_text(encoding="utf-8")
        for i, line in enumerate(content.splitlines(), 1):
            stripped = line.strip()
            # Skip comments and empty lines
            if stripped.startswith("#") or not stripped:
                continue
            # Check for print() calls - use regex to match actual print() function calls
            # This pattern matches: print( ... ) but not words like "Blueprint" or "printf"
            if re.search(r'\bprint\s*\(', stripped):
                # Allow print in specific contexts
                allowed_patterns = [
                    "print(debug",
                    'print("DEBUG',
                    'print(f"DEBUG',
                    'print("INFO',
                    'print(f"INFO',
                ]
                if not any(pattern in stripped for pattern in allowed_patterns):
                    errors.append(f"{filepath}:{i}: print() statement found: {stripped[:120]}")
    except Exception as e:
        errors.append(f"{filepath}: Error reading file: {e}")
    return errors


def find_python_files(path: Path) -> list:
    """Find all Python files in a path recursively."""
    if path.is_file():
        return [path] if path.suffix == ".py" else []
    files = []
    for f in path.rglob("*.py"):
        files.append(f)
    return files


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: no_print_check.py <file1> [file2] ...")
        sys.exit(1)

    # Directories to exclude from print check
    exclude_dirs = {"tests", "scripts", "docs", "alembic", "cli", "presets"}

    all_errors = []
    for arg in sys.argv[1:]:
        filepath = Path(arg)
        # Find all Python files
        python_files = find_python_files(filepath)
        for py_file in python_files:
            # Skip excluded directories
            if any(part in exclude_dirs for part in py_file.parts):
                continue
            errors = check_file(py_file)
            all_errors.extend(errors)

    if all_errors:
        for error in all_errors:
            print(error)
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()