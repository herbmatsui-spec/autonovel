#!/usr/bin/env python3
"""
Simple script to extract UI asset prompts from React/TSX components.
For demonstration, it extracts known patterns from a few components.
In practice, you could extend this to parse AST or use regex for more components.
"""
import json
import os
import re
from pathlib import Path

# Base directory of the frontend
FRONTEND_DIR = Path(__file__).parent.parent / "frontend"
OUTPUT_FILE = Path(__file__).parent / "prompts" / "ui_asset_prompts.json"

def extract_from_button():
    """Extract prompt for Button component."""
    button_path = FRONTEND_DIR / "src" / "components" / "common" / "Button.tsx"
    if not button_path.exists():
        return None
    # Read file content
    content = button_path.read_text(encoding="utf-8")
    # Look for style props or className that indicate button styling
    # We'll just return a fixed prompt for demonstration
    return {
        "assetType": "button",
        "componentPath": str(button_path.relative_to(FRONTEND_DIR.parent)),
        "prompt": "A modern UI button with {color} background, {borderRadius} radius, subtle {shadow} shadow, flat design, suitable for a fantasy novel app",
        "variables": {
            "color": "deep indigo",
            "borderRadius": "8px",
            "shadow": "soft drop"
        },
        "samplePrompt": "A modern UI button with deep indigo background, 8px radius, subtle soft drop shadow, flat design, suitable for a fantasy novel app"
    }

def extract_from_applayout():
    """Extract prompt for header background from AppLayout."""
    layout_path = FRONTEND_DIR / "src" / "components" / "layout" / "AppLayout.tsx"
    if not layout_path.exists():
        return None
    return {
        "assetType": "header-bg",
        "componentPath": str(layout_path.relative_to(FRONTEND_DIR.parent)),
        "prompt": "A wide header background for a web novel site, {color} gradient, {texture} texture, fantasy style",
        "variables": {
            "color": "dark to purple gradient",
            "texture": "soft parchment"
        },
        "samplePrompt": "A wide header background for a web novel site, dark to purple gradient, soft parchment texture, fantasy style"
    }

def extract_from_bookcoverpreview():
    """Extract prompt for card background from BookCoverPreview."""
    cover_path = FRONTEND_DIR / "src" / "components" / "showcase" / "BookCoverPreview.tsx"
    if not cover_path.exists():
        return None
    return {
        "assetType": "card-bg",
        "componentPath": str(cover_path.relative_to(FRONTEND_DIR.parent)),
        "prompt": "A fantasy card panel with parchment texture, faint rune borders, soft drop shadow, suitable for displaying novel covers",
        "variables": {},
        "samplePrompt": "A fantasy card panel with parchment texture, faint rune borders, soft drop shadow, suitable for displaying novel covers"
    }

def extract_from_spinner():
    """Extract prompt for loading spinner."""
    # We don't have a spinner component yet, but we can propose one
    return {
        "assetType": "spinner",
        "componentPath": "proposed: src/components/common/Spinner.tsx",
        "prompt": "A cute animated loading spinner in fantasy style: glowing orb with tiny stars orbiting, transparent background, 64x64",
        "variables": {},
        "samplePrompt": "A cute animated loading spinner in fantasy style: glowing orb with tiny stars orbiting, transparent background, 64x64"
    }

def extract_from_icon():
    """Extract prompt for an icon (e.g., settings gear)."""
    return {
        "assetType": "icon",
        "componentPath": "proposed: src/components/common/Icons.tsx",
        "prompt": "A fantasy-style gear icon: ornate metal gear with small gem inlay, flat design, transparent background, 64x64",
        "variables": {},
        "samplePrompt": "A fantasy-style gear icon: ornate metal gear with small gem inlay, flat design, transparent background, 64x64"
    }

def main():
    prompts = []
    for extractor in [extract_from_button, extract_from_applayout, extract_from_bookcoverpreview, extract_from_spinner, extract_from_icon]:
        res = extractor()
        if res:
            prompts.append(res)
    # Ensure output directory exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(prompts, f, ensure_ascii=False, indent=2)
    print(f"Extracted {len(prompts)} UI asset prompts to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()