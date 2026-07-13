import pathlib


def generate_deps_mermaid(start_path: str, output_file: str):
    """
    Simple dependency analyzer that scans imports in .py files 
    and generates a Mermaid graph.
    """
    import re

    root = pathlib.Path(start_path).resolve()
    dependencies = []
    # Regex to find 'from x import y' or 'import x'
    import_re = re.compile(r'^(?:from\s+([\w\.]+)\s+import|import\s+([\w\.]+))', re.MULTILINE)

    for path in root.rglob("*.py"):
        if any(ex in str(path) for ex in {'.git', '__pycache__', 'tests', 'venv'}):
            continue

        module_name = path.relative_to(root).with_suffix('').as_posix().replace('/', '.')

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                for match in import_re.finditer(content):
                    imported = match.group(1) or match.group(2)
                    # Only track internal imports
                    if imported.startswith('src') or imported.startswith('streamlit_app') or imported.startswith('config'):
                        dependencies.append((module_name, imported))
        except Exception:
            continue

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("# Module Dependencies\n\n")
        f.write("```mermaid\ngraph TD\n")
        for source, target in set(dependencies):
            f.write(f"    {source} --> {target}\n")
        f.write("```\n")

if __name__ == "__main__":
    project_root = pathlib.Path(__file__).parents[1]
    output = project_root / "docs" / "architecture" / "deps.md"
    output.parent.mkdir(parents=True, exist_ok=True)

    generate_deps_mermaid(str(project_root), str(output))
    print(f"Dependency graph generated at {output}")
