#!/usr/bin/env python3
"""
Step 14: Quality gate validator for subtext Jinja2 templates (PLAN_Y2).
Validates YAML frontmatter, line count limits, and syntax.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.narrative.subtext_templates.loader import TemplateLoader
from src.narrative.subtext_templates.renderer import TemplateRenderer


def validate_all_templates(template_dir: Path = Path("templates/subtext")) -> list[str]:
    loader = TemplateLoader(template_dir)
    renderer = TemplateRenderer(template_dir=template_dir, loader=loader)
    templates = loader.load_all(force_reload=True)

    errors: list[str] = []
    print(f"=== Validating Subtext Templates in {template_dir} ===")
    print(f"Found {len(templates)} templates.\n")

    for tid, cand in templates.items():
        # 1. Validate metadata fields
        meta = cand.metadata
        if not meta.id:
            errors.append(f"[{tid}] Missing ID.")
        if meta.weight <= 0:
            errors.append(f"[{tid}] Weight must be positive, got {meta.weight}.")

        # 2. Render dry-run with defaults
        rendered = renderer.render(cand)
        if not rendered.raw_text.strip():
            errors.append(f"[{tid}] Rendered output is empty.")
            continue

        dialogue_count = sum(1 for line in rendered.lines if line.type == "dialogue")
        beat_action_count = sum(1 for line in rendered.lines if line.type in ["beat", "action"])

        # Quality check: dialogue lines <= 2
        if dialogue_count > 2:
            errors.append(f"[{tid}] Too many dialogue lines ({dialogue_count} > 2). Keep dialogue sparse.")

        # Quality check: stage direction >= 1 (unless action-only or minimal beat)
        if beat_action_count < 1 and not tid.startswith("action."):
            errors.append(f"[{tid}] Missing stage direction beat/action. Subtext requires at least 1 beat.")

        print(f"  [OK] {tid:35s} (dialogue: {dialogue_count}, beats/actions: {beat_action_count})")

    return errors


def main() -> int:
    errs = validate_all_templates()
    if errs:
        print("\nValidation Failed with errors:")
        for e in errs:
            print(f"  - {e}")
        return 1

    print("\nAll templates passed quality validation successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
