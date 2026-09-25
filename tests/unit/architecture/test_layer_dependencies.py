"""
Architectural Layer Dependency Tests.

Ensures Clean Architecture rules:
1. Domain layer (src/domain/) must never depend on presentation/routing layers
   (e.g., src.backend.routers, fastapi router modules).
"""
import ast
from pathlib import Path
import pytest


def get_imports_from_file(file_path: Path) -> list[tuple[int, str]]:
    """Parse a python file using AST and return a list of (line_no, module_name)."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    try:
        tree = ast.parse(content, filename=str(file_path))
    except SyntaxError as e:
        pytest.fail(f"Syntax error in {file_path}: {e}")

    imported_modules: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_modules.append((node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported_modules.append((node.lineno, node.module))
            elif node.level > 0:
                # Relative import (e.g. from . import foo)
                pass

    return imported_modules


def test_domain_layer_does_not_import_routers():
    """Verify that no file under src/domain/ imports from src.backend.routers or routers."""
    repo_root = Path(__file__).resolve().parents[3]
    domain_dir = repo_root / "src" / "domain"

    assert domain_dir.exists(), f"Domain directory {domain_dir} does not exist"

    violations: list[str] = []
    forbidden_prefixes = (
        "src.backend.routers",
        "backend.routers",
        "src.routers",
        "routers",
    )

    domain_py_files = list(domain_dir.rglob("*.py"))
    assert len(domain_py_files) > 0, "No python files found in src/domain"

    for py_file in domain_py_files:
        imports = get_imports_from_file(py_file)
        rel_path = py_file.relative_to(repo_root)

        for lineno, mod_name in imports:
            for forbidden in forbidden_prefixes:
                if mod_name == forbidden or mod_name.startswith(f"{forbidden}."):
                    violations.append(
                        f"{rel_path}:{lineno} imports forbidden module '{mod_name}'"
                    )

    assert not violations, (
        f"Domain layer has architectural dependency violations:\n"
        + "\n".join(violations)
    )
