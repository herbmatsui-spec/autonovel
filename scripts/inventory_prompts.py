#!/usr/bin/env python
"""Prompt Inventory - Scan all prompt files and extract metadata"""

import csv
import re
from pathlib import Path
from typing import Any, Dict, List

PROMPTS_ROOT = Path("prompts")
OUTPUT_CSV = Path("docs/prompts_inventory.csv")

def extract_jinja_variables(content: str) -> List[str]:
    """Extract {{ variable }} patterns from Jinja2 template."""
    pattern = r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_.]*)\s*\}\}'
    matches = re.findall(pattern, content)
    return list(set(matches))

def extract_meta_block(content: str) -> Dict[str, str]:
    """Extract META: key: value blocks from template."""
    meta = {}
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('# META:') or line.startswith('// META:') or line.startswith('-- META:'):
            # Parse "key: value"
            parts = line.split(':', 2)
            if len(parts) >= 3:
                key = parts[1].strip()
                value = parts[2].strip()
                meta[key] = value
    return meta

def analyze_prompt_file(filepath: Path) -> Dict[str, Any]:
    """Analyze a single prompt file."""
    try:
        content = filepath.read_text(encoding='utf-8')
    except UnicodeDecodeError:
        content = filepath.read_text(encoding='utf-8', errors='ignore')

    lines = content.split('\n')
    line_count = len(lines)
    char_count = len(content)

    variables = extract_jinja_variables(content)
    meta = extract_meta_block(content)

    # Determine template type from path
    rel_path = filepath.relative_to(PROMPTS_ROOT)
    template_type = rel_path.parts[0] if rel_path.parts else 'root'

    return {
        'file_path': str(rel_path),
        'template_type': template_type,
        'line_count': line_count,
        'char_count': char_count,
        'variable_count': len(variables),
        'variables': ';'.join(sorted(variables)),
        'has_meta': len(meta) > 0,
        'meta_keys': ';'.join(sorted(meta.keys())),
        'meta_values': ';'.join(meta.values()),
    }

def main():
    if not PROMPTS_ROOT.exists():
        print(f"Prompts directory not found: {PROMPTS_ROOT}")
        return

    # Find all template files
    extensions = ('.j2', '.jinja2', '.jinja', '.tmpl', '.txt', '.md', '.py')
    prompt_files = []
    for ext in extensions:
        prompt_files.extend(PROMPTS_ROOT.rglob(f'*{ext}'))

    # Also include files without extension that might be templates
    for f in PROMPTS_ROOT.rglob('*'):
        if f.is_file() and f.suffix == '':
            prompt_files.append(f)

    # Deduplicate
    prompt_files = list(set(prompt_files))
    prompt_files.sort()

    print(f"Found {len(prompt_files)} prompt files")

    # Analyze each file
    inventory = []
    for f in prompt_files:
        info = analyze_prompt_file(f)
        inventory.append(info)

    # Write CSV
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ['file_path', 'template_type', 'line_count', 'char_count',
                  'variable_count', 'variables', 'has_meta', 'meta_keys', 'meta_values']

    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in inventory:
            writer.writerow(row)

    print(f"Inventory saved to {OUTPUT_CSV}")

    # Summary statistics
    total_lines = sum(r['line_count'] for r in inventory)
    total_chars = sum(r['char_count'] for r in inventory)
    total_vars = sum(r['variable_count'] for r in inventory)
    types = {}
    for r in inventory:
        types[r['template_type']] = types.get(r['template_type'], 0) + 1

    print("\nSummary:")
    print(f"  Total files: {len(inventory)}")
    print(f"  Total lines: {total_lines}")
    print(f"  Total chars: {total_chars}")
    print(f"  Total variables: {total_vars}")
    print(f"  By type: {types}")

if __name__ == '__main__':
    main()
