#!/usr/bin/env python3
"""
Step 23: Validate synchronization between prompt template tokens and token dictionary (PLAN_Y3).
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from src.narrative.subtext_tokens.expander import TokenExpander
from src.narrative.subtext_tokens.parser import TokenParser


def validate_prompt_token_sync(
    prompt_path: Path = Path("prompts/templates/narrative/dialogue_generation.j2"),
    dict_path: Path = Path("data/subtext/tokens.yaml"),
) -> list[str]:
    if not prompt_path.exists():
        return [f"Prompt file not found: {prompt_path}"]
    if not dict_path.exists():
        return [f"Token dictionary file not found: {dict_path}"]

    prompt_content = prompt_path.read_text(encoding="utf-8")
    tokens = TokenParser.find_tokens(prompt_content)
    expander = TokenExpander(dict_path=dict_path)

    print(f"=== Validating Prompt Tokens against Dictionary ===")
    print(f"Prompt: {prompt_path}")
    print(f"Dictionary: {dict_path}")
    print(f"Found {len(tokens)} token mentions in prompt.\n")

    errors: list[str] = []
    seen = set()
    for tok in tokens:
        if tok.raw in seen:
            continue
        seen.add(tok.raw)

        resolved = expander.resolve_token(tok)
        if resolved is None:
            # Token failed to resolve to a dictionary definition
            errors.append(f"Unresolved prompt token: {tok.raw} (path: {tok.full_path()})")
        else:
            print(f"  [OK] {tok.raw:30s} -> {resolved[:40]}")

    return errors


def main() -> int:
    errs = validate_prompt_token_sync()
    if errs:
        print("\nValidation Failed:")
        for e in errs:
            print(f"  - {e}")
        return 1

    print("\nAll prompt tokens resolved successfully in the token dictionary!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
