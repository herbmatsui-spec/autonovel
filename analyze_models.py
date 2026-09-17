import ast
import sys

files = [
    'E:/hhh/src/models/audit.py',
    'E:/hhh/src/models/base.py',
    'E:/hhh/src/models/beat_sheet.py',
    'E:/hhh/src/models/bible.py',
    'E:/hhh/src/models/character.py',
    'E:/hhh/src/models/db.py',
    'E:/hhh/src/models/emotional_hook.py',
    'E:/hhh/src/models/entertainment_check.py',
    'E:/hhh/src/models/illustration.py',
    'E:/hhh/src/models/marketing.py',
    'E:/hhh/src/models/narrative_metrics.py',
    'E:/hhh/src/models/narrative_metrics_db.py',
    'E:/hhh/src/models/planning_config.py',
    'E:/hhh/src/models/plot.py',
    'E:/hhh/src/models/production_config.py',
    'E:/hhh/src/models/prompt_version.py',
    'E:/hhh/src/models/report.py',
    'E:/hhh/src/models/sharp_edge.py',
    'E:/hhh/src/models/task.py',
    'E:/hhh/src/models/world.py',
    'E:/hhh/src/models/writing.py',
    'E:/hhh/src/models/editor.py',
]

for f in files:
    with open(f, 'r', encoding='utf-8') as fp:
        content = fp.read()
    tree = ast.parse(content)
    classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    imports = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for alias in n.names:
                imports.append(alias.name)
        elif isinstance(n, ast.ImportFrom):
            if n.module:
                for alias in n.names:
                    imports.append(f'{n.module}.{alias.name}')
    print(f'=== {f.split("/")[-1]} ===')
    print(f'Classes: {classes}')
    print(f'Functions: {funcs}')
    print(f'Imports: {imports[:10]}')
    print()
EOF