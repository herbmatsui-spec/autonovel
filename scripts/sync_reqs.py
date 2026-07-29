#!/usr/bin/env python3
"""
Generate requirements.txt from pyproject.toml's [project.dependencies] section.

This script reads the dependencies listing in pyproject.toml and creates a
requirements.txt file containing the same packages, one per line. It will
overwrite whatever exists in requirements.txt.
"""

import sys
from pathlib import Path


def sync_dependencies() -> None:
    pyproject_path = Path("pyproject.toml")
    reqs_path = Path("requirements.txt")

    if not pyproject_path.is_file():
        print("Error: pyproject.toml not found.", file=sys.stderr)
        sys.exit(1)

    dependencies: list[str] = []

    with pyproject_path.open("r", encoding="utf-8") as f:
        lines = f.readlines()

    in_deps = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("dependencies = ["):
            in_deps = True
            continue
        if in_deps:
            if stripped == "]":
                break
            # Remove trailing comma, then surrounding double quotes
            dep = stripped.rstrip(",").strip('"')
            if dep:
                dependencies.append(dep)

    with reqs_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(dependencies) + "\n")

    print(f"Successfully synced {len(dependencies)} dependencies to requirements.txt")


if __name__ == "__main__":
    sync_dependencies()
