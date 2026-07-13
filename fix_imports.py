import os
import re

BACKEND_MODULES = [
    "database",
    "engine",
    "engine_agents_legacy",
    "engine_context",
    "engine_critique",
    "engine_narrative",
    "engine_prompts",
    "engine_reader",
    "engine_style_rag",
    "engine_utils",
    "background",
    "config",
    "config_legacy",
    "models_legacy",
    "redis_util",
    "sanitizer",
    "server",
    "tasks",
    "worker_config",
    "workflows"
]

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        encoding_used = 'utf-8'
    except UnicodeDecodeError:
        print(f"Skipping {filepath} due to encoding errors")
        return

    original = content

    for mod in BACKEND_MODULES:
        # from {mod} import ... -> from backend.{mod} import ...
        pattern_from = rf'^(\s*)from\s+{mod}(\s+import|\.)'
        content = re.sub(pattern_from, rf'\1from backend.{mod}\2', content, flags=re.MULTILINE)

        # import {mod} -> from backend import {mod}
        pattern_import = rf'^(\s*)import\s+{mod}(\s*)$'
        content = re.sub(pattern_import, rf'\1from backend import {mod}\2', content, flags=re.MULTILINE)

    if content != original:
        with open(filepath, 'w', encoding=encoding_used) as f:
            f.write(content)
        print(f"Fixed imports in: {filepath}")

def main():
    root = os.path.dirname(os.path.abspath(__file__))
    target_dirs = ['backend', 'services', 'core', 'agents', 'tests', 'shared']
    for tdir in target_dirs:
        for dirpath, dirnames, filenames in os.walk(os.path.join(root, tdir)):
            if any(ignore in dirpath for ignore in ['.git', '.venv', 'venv', '__pycache__', '.tmp']):
                continue

            for file in filenames:
                if file.endswith('.py') and file != 'fix_imports.py':
                    fix_file(os.path.join(dirpath, file))

if __name__ == '__main__':
    main()

