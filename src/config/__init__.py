"""Configuration package.

This package loads the STYLE_DEFINITIONS from the styles.json file.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

__all__ = ["STYLE_DEFINITIONS"]

try:
    # Get the directory of this __init__.py file: /app/src/config
    # We want to go up two levels to get to /app, then into config/data/styles.json
    CONFIG_DIR = Path(__file__).resolve().parents[2]  # /app
    STYLES_JSON_PATH = CONFIG_DIR / "config" / "data" / "styles.json"
    with open(STYLES_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    STYLE_DEFINITIONS = data.get("STYLE_DEFINITIONS", {})
except Exception as e:
    # In case of error, log and set to empty dict
    logger = logging.getLogger(__name__)
    logger.error(f"Failed to load STYLE_DEFINITIONS from {STYLES_JSON_PATH}: {e}")
    STYLE_DEFINITIONS = {}