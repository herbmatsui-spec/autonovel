#!/usr/bin/env python3
"""
Generate UI assets using an offline image generation model.
This example uses a placeholder: it creates dummy colored images.
Replace the generation logic with your preferred offline model (e.g., Stable Diffusion via API, diffusers, etc.).
"""
import json
import os
import base64
import io
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

PROMPT_FILE = Path(__file__).parent / "prompts" / "ui_asset_prompts.json"
OUT_DIR = Path(__file__).parent.parent / "static" / "generated-ui-assets"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Simple color mapping for demonstration
COLOR_MAP = {
    "deep indigo": (79, 70, 229),   # Indigo-600
    "dark to purple gradient": (100, 50, 150),  # Approximate
    "soft parchment": (245, 240, 220),
}

def create_dummy_image(prompt, width=512, height=512, asset_type="unknown"):
    """Create a dummy image based on prompt keywords (for demonstration)."""
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    # Try to get a font; if not available, use default.
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font = ImageFont.load_default()
    # Draw a simple rectangle with color based on prompt
    color = (100, 150, 200)  # default blue-gray
    if "indigo" in prompt.lower():
        color = COLOR_MAP["deep indigo"]
    elif "purple" in prompt.lower():
        color = (120, 80, 180)
    elif "parchment" in prompt.lower():
        color = COLOR_MAP["soft parchment"]
    elif "golden" in prompt.lower():
        color = (212, 175, 55)
    draw.rectangle([0, 0, width, height], fill=color)
    # Add text
    text = asset_type
    # Use textbbox for Pillow >= 8.0.0
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    draw.text(((width - w) / 2, (height - h) / 2), text, fill=(255, 255, 255), font=font)
    return img

def main():
    if not PROMPT_FILE.exists():
        print(f"Prompt file not found: {PROMPT_FILE}")
        return
    with open(PROMPT_FILE, encoding="utf-8") as f:
        items = json.load(f)
    for it in items:
        prompt = it.get("samplePrompt", it.get("prompt", ""))
        asset_type = it.get("assetType", "asset")
        # For demonstration, we use fixed size; you can make it configurable.
        img = create_dummy_image(prompt, width=512, height=512, asset_type=asset_type)
        # Create a filename: asset_type + hash of prompt to avoid collisions
        import hashlib
        hash_suffix = hashlib.sha256(prompt.encode()).hexdigest()[:8]
        fname = f"{asset_type}_{hash_suffix}.png"
        out_path = OUT_DIR / fname
        img.save(out_path)
        print(f"Generated {out_path}")
    print(f"All images saved to {OUT_DIR}")

if __name__ == "__main__":
    main()