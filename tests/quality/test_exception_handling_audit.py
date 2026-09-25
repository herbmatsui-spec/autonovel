"""
Audit test to detect silent exception swallowing (except Exception: pass).
Uses Python AST to ensure all exception handlers log or handle exceptions.
"""

import ast
from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

WORKFLOW_DIRS = [
    REPO_ROOT / "src" / "backend" / "workflows",
]


def is_silent_pass(handler: ast.ExceptHandler) -> bool:
    """Check if an except handler only contains 'pass' or ellipsis without logging."""
    if len(handler.body) == 1:
        stmt = handler.body[0]
        if isinstance(stmt, ast.Pass):
            return True
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is ...:
            return True
    return False


def find_silent_exceptions(filepath: Path) -> list[tuple[int, str]]:
    """Parse python file and find line numbers of silent except Exception blocks."""
    try:
        content = filepath.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(filepath))
    except Exception:
        return []

    silent_catches = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            # Check if handling broad Exception or bare except
            is_broad = False
            if node.type is None:
                is_broad = True
            elif isinstance(node.type, ast.Name) and node.type.id in ("Exception", "BaseException"):
                is_broad = True
            
            if is_broad and is_silent_pass(node):
                silent_catches.append((node.lineno, "except Exception: pass (silent swallow)"))
    return silent_catches


def test_no_silent_exception_swallowing_in_workflows():
    """Verify that workflows do not silently swallow broad exceptions with pass."""
    violations = []

    for directory in WORKFLOW_DIRS:
        if not directory.exists():
            continue
        for py_file in directory.rglob("*.py"):
            rel_path = py_file.relative_to(REPO_ROOT).as_posix()
            silent_catches = find_silent_exceptions(py_file)
            for lineno, desc in silent_catches:
                violations.append(f"{rel_path}:{lineno} -> {desc}")

    assert not violations, (
        f"Found {len(violations)} silent exception catch(es) in workflows/services:\n"
        + "\n".join(violations)
    )
