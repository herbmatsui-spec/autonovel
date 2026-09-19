"""
Character profile constraints and speech filter for subtext templates (Step 16).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

logger = logging.getLogger("narrative.subtext_templates.constraints")


class CharacterConstraints:
    """Handles character-specific template filtering and dialogue speech post-processing."""

    def __init__(self, config_path: Optional[str | Path] = None) -> None:
        self.config_path = Path(config_path or "config/character_profiles.yaml")
        self.profiles: Dict[str, Any] = {}
        self.load_profiles()

    def load_profiles(self) -> None:
        if self.config_path.exists():
            try:
                data = yaml.safe_load(self.config_path.read_text(encoding="utf-8")) or {}
                self.profiles = data.get("characters", {})
            except Exception as e:
                logger.warning(f"Failed to load character profiles from {self.config_path}: {e}")
                self.profiles = {}

    def get_profile(self, character_name: str) -> Dict[str, Any]:
        key = character_name.lower().strip()
        return self.profiles.get(key, self.profiles.get("default", {}))

    def is_template_allowed(self, character_name: str, template_tags: List[str]) -> bool:
        """Checks whether template tags conflict with forbidden_tags."""
        profile = self.get_profile(character_name)
        forbidden = set(profile.get("forbidden_tags", []))
        return len(forbidden.intersection(template_tags)) == 0

    def apply_speech_patterns(self, character_name: str, text: str) -> str:
        """Applies character speech patterns to dialogue text."""
        profile = self.get_profile(character_name)
        patterns = profile.get("speech_patterns", {})
        res = text
        for orig, replacement in patterns.items():
            res = res.replace(orig, replacement)
        return res
