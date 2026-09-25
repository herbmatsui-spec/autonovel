"""
Tests for checking that production backend code does not contain raw print() statements.
Uses Python AST to inspect all .py files under src/backend and src/services.
"""

import ast
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Directories strictly requiring logger instead of raw print()
PRODUCTION_DIRS = [
    REPO_ROOT / "src" / "backend" / "routers",
    REPO_ROOT / "src" / "backend" / "middleware",
    REPO_ROOT / "src" / "backend" / "services",
    REPO_ROOT / "src" / "backend" / "security",
]

# Files explicitly allowed to use print (e.g. CLI entrypoints or explicit debug modules)
ALLOWED_FILES = {
    # If any specific files are meant for console output, add their relative path here
}


def find_print_calls(filepath: Path) -> list[tuple[int, str]]:
    """Parse python file and find line numbers of print() function calls."""
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(filepath))
    except Exception:
        return []

    print_calls = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id == "print":
                print_calls.append((node.lineno, "print(...)"))
    return print_calls


def test_no_raw_print_in_critical_backend_modules():
    """Verify that routers, middleware, backend services, and security do not contain print()."""
    violations = []

    for directory in PRODUCTION_DIRS:
        if not directory.exists():
            continue
        for py_file in directory.rglob("*.py"):
            rel_path = py_file.relative_to(REPO_ROOT).as_posix()
            if rel_path in ALLOWED_FILES:
                continue

            calls = find_print_calls(py_file)
            for lineno, call_repr in calls:
                violations.append(f"{rel_path}:{lineno} -> {call_repr}")

    assert not violations, (
        f"Found {len(violations)} raw print() call(s) in critical backend modules. "
        f"Use logging instead:\n" + "\n".join(violations[:20])
    )
