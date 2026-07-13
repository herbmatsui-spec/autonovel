import pathlib


def generate_tree(start_path: str, output_file: str):
    """
    Generates a Markdown-formatted directory tree of the project.
    Excludes common noise directories like .git, __pycache__, etc.
    """
    exclude_dirs = {
        '.git', '__pycache__', '.mypy_cache', '.pytest_cache',
        '.dockerignore', '.gitignore', 'htmlcov', '.test_venv'
    }

    # Fix: Use a set for exclude_dirs properly
    exclude_set = {
        '.git', '__pycache__', '.mypy_cache', '.pytest_cache',
        '.dockerignore', '.gitignore', 'htmlcov', '.test_venv'
    }

    tree_lines = []

    def walk(path, prefix=""):
        try:
            entries = sorted(list(path.iterdir()), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            return

        for i, entry in enumerate(entries):
            if entry.name in exclude_set:
                continue

            is_last = (i == len(entries) - 1)
            connector = "└── " if is_last else "├── "

            tree_lines.append(f"{prefix}{connector}{entry.name}")

            if entry.is_dir():
                extension = "    " if is_last else "│   "
                walk(entry, prefix + extension)

    root = pathlib.Path(start_path).resolve()
    tree_lines.append(f"**Root: {root}**")
    walk(root)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Project Structure\n\n")
        f.write("```text\n")
        f.write("\n".join(tree_lines))
        f.write("\n```\n")

if __name__ == "__main__":
    # Root of the project is 2 levels up from this script (scripts/gen_tree.py)
    project_root = pathlib.Path(__file__).parents[1]
    output = project_root / "docs" / "architecture" / "structure.md"
    output.parent.mkdir(parents=True, exist_ok=True)

    generate_tree(str(project_root), str(output))
    print(f"Tree generated at {output}")
