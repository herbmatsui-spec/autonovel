"""
TemplateLoader for Subtext Template Library (PLAN_Y2 Step 3).
Parses frontmatter, scans directory, and maintains index cache.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from src.narrative.subtext_templates.models import TemplateCandidate, TemplateMetadata

logger = logging.getLogger("narrative.subtext_templates.loader")


class TemplateLoader:
    """Discovers, parses, and indexes subtext templates with frontmatter."""

    def __init__(self, template_dir: Optional[str | Path] = None) -> None:
        self.template_dir = Path(template_dir or "templates/subtext").resolve()
        self._cache: Dict[str, TemplateCandidate] = {}
        self._last_mtime: float = 0.0

    def parse_template_file(self, file_path: Path) -> Optional[TemplateCandidate]:
        """Parses a single .j2 file extracting YAML frontmatter and Jinja body."""
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to read template {file_path}: {e}")
            return None

        # Extract frontmatter between leading --- delimiters
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter_raw = parts[1]
                jinja_body = parts[2].strip()
                try:
                    meta_dict = yaml.safe_load(frontmatter_raw) or {}
                except Exception as e:
                    logger.error(f"Malformed YAML frontmatter in {file_path}: {e}")
                    return None
            else:
                meta_dict = {}
                jinja_body = content.strip()
        else:
            meta_dict = {}
            jinja_body = content.strip()

        # Deduce id from file path if not present
        template_id = meta_dict.get("id")
        if not template_id:
            rel = file_path.relative_to(self.template_dir)
            template_id = str(rel.with_suffix("")).replace(os.sep, ".").replace("/", ".")
            meta_dict["id"] = template_id

        # Determine category from parent directory if not set
        if not meta_dict.get("category"):
            parent_name = file_path.parent.name
            if parent_name != "subtext":
                meta_dict["category"] = parent_name

        try:
            metadata = TemplateMetadata(**meta_dict)
        except Exception as e:
            logger.error(f"Invalid metadata for {file_path}: {e}")
            return None

        return TemplateCandidate(
            id=metadata.id,
            metadata=metadata,
            score=float(metadata.weight),
            template_content=jinja_body,
            file_path=str(file_path),
        )

    def load_all(self, force_reload: bool = False) -> Dict[str, TemplateCandidate]:
        """Loads all templates, updating the cache if directory mtime changed."""
        if not self.template_dir.exists():
            logger.warning(f"Template directory does not exist: {self.template_dir}")
            return {}

        current_mtime = max(
            [p.stat().st_mtime for p in self.template_dir.rglob("*.j2")] or [0.0]
        )
        if not force_reload and self._cache and current_mtime <= self._last_mtime:
            return self._cache

        candidates: Dict[str, TemplateCandidate] = {}
        for p in self.template_dir.rglob("*.j2"):
            if p.name.startswith("_"):
                continue  # Skip _base.j2 or partials
            candidate = self.parse_template_file(p)
            if candidate:
                candidates[candidate.id] = candidate

        self._cache = candidates
        self._last_mtime = current_mtime
        self._save_index(candidates)
        return self._cache

    def _save_index(self, candidates: Dict[str, TemplateCandidate]) -> None:
        """Saves catalog index to templates/subtext/index.yaml."""
        index_data = {
            "templates": {
                cid: {
                    "id": c.metadata.id,
                    "category": c.metadata.category,
                    "tags": c.metadata.tags,
                    "weight": c.metadata.weight,
                    "final": c.metadata.final,
                    "file": c.file_path,
                }
                for cid, c in candidates.items()
            }
        }
        index_path = self.template_dir / "index.yaml"
        try:
            with open(index_path, "w", encoding="utf-8") as f:
                yaml.dump(index_data, f, allow_unicode=True, sort_keys=False)
        except Exception as e:
            logger.warning(f"Could not save index to {index_path}: {e}")

    def get_template(self, template_id: str) -> Optional[TemplateCandidate]:
        all_templates = self.load_all()
        return all_templates.get(template_id)
