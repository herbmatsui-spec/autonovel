"""
TemplateRenderer: Jinja2-based renderer with custom subtext filters and fallback chain (PLAN_Y2 Step 5, 6, 18).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import jinja2
import yaml

from src.narrative.subtext_engine.models import SubtextContext
from src.narrative.subtext_templates.constraints import CharacterConstraints
from src.narrative.subtext_templates.loader import TemplateLoader
from src.narrative.subtext_templates.models import (
    RenderedDialogue,
    RenderedLine,
    TemplateCandidate,
)

logger = logging.getLogger("narrative.subtext_templates.renderer")


def filter_beat(val: Any) -> str:
    return f"（{val}）"


def filter_action(val: Any) -> str:
    return f"——{val}。"


def filter_irony(val: Any) -> str:
    return f"「……{val}」"


def filter_pause(val: Any) -> str:
    return f"……{val}"


def filter_glance(val: Any) -> str:
    return f"（視線を落とし、{val}）"


class TemplateRenderer:
    """Renders subtext templates into structured RenderedDialogue."""

    def __init__(
        self,
        template_dir: Optional[str | Path] = None,
        loader: Optional[TemplateLoader] = None,
        constraints: Optional[CharacterConstraints] = None,
    ) -> None:
        self.template_dir = Path(template_dir or "templates/subtext").resolve()
        self.loader = loader or TemplateLoader(self.template_dir)
        self.constraints = constraints or CharacterConstraints()

        # Jinja2 environment setup
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.template_dir)),
            autoescape=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

        # Step 5: Custom filters
        self.jinja_env.filters["beat"] = filter_beat
        self.jinja_env.filters["action"] = filter_action
        self.jinja_env.filters["irony"] = filter_irony
        self.jinja_env.filters["pause"] = filter_pause
        self.jinja_env.filters["glance"] = filter_glance

        # Shared vocabularies
        self.shared_data = self._load_shared_vocabularies()

    def _load_shared_vocabularies(self) -> Dict[str, Any]:
        """Step 13: Loads shared data dictionaries from data/subtext/."""
        data: Dict[str, Any] = {"beats": {}, "actions": {}, "irony_phrases": {}}
        data_dir = Path("data/subtext")
        if data_dir.exists():
            for key in ["beats", "actions", "irony_phrases"]:
                fp = data_dir / f"{key}.yaml"
                if fp.exists():
                    try:
                        data[key] = yaml.safe_load(fp.read_text(encoding="utf-8")) or {}
                    except Exception as e:
                        logger.warning(f"Failed to load {fp}: {e}")
        return data

    def render(
        self,
        candidate_or_id: str | TemplateCandidate,
        variables: Optional[Dict[str, Any]] = None,
        context: Optional[SubtextContext] = None,
    ) -> RenderedDialogue:
        """Step 6 & Step 18: Renders template with fallback chain."""
        ctx = context or SubtextContext()
        vars_dict = dict(variables or {})
        # Provide shared vocabularies and context to template
        render_ctx = {
            **self.shared_data,
            **vars_dict,
            "speaker": ctx.speaker,
            "target": ctx.target_speaker,
            "emotion": ctx.emotion,
            "context": ctx,
        }

        # Step 18: Fallback chain
        candidate = (
            candidate_or_id
            if isinstance(candidate_or_id, TemplateCandidate)
            else self.loader.get_template(candidate_or_id)
        )

        template_id = candidate.id if candidate else str(candidate_or_id)
        rendered_text = ""
        used_id = template_id

        # 1. Try rendering primary template
        if candidate and candidate.template_content:
            try:
                tmpl = self.jinja_env.from_string(candidate.template_content)
                rendered_text = tmpl.render(render_ctx)
            except Exception as e:
                logger.warning(f"Failed to render template {template_id}: {e}. Falling back.")

        # 2. Try generic_subtext fallback
        if not rendered_text.strip():
            generic_cand = self.loader.get_template("fallback.generic_subtext")
            if generic_cand:
                try:
                    tmpl = self.jinja_env.from_string(generic_cand.template_content)
                    rendered_text = tmpl.render(render_ctx)
                    used_id = "fallback.generic_subtext"
                except Exception:
                    pass

        # 3. Try minimal_beat fallback
        if not rendered_text.strip():
            minimal_cand = self.loader.get_template("fallback.minimal_beat")
            if minimal_cand:
                try:
                    tmpl = self.jinja_env.from_string(minimal_cand.template_content)
                    rendered_text = tmpl.render(render_ctx)
                    used_id = "fallback.minimal_beat"
                except Exception:
                    pass

        # 4. Final hardcoded fallback
        if not rendered_text.strip():
            rendered_text = "（言葉を呑み込み、静かに視線を落とす）"
            used_id = "hardcoded_fallback"

        # Apply character speech pattern post-filtering if speaker known (Step 16)
        if ctx.speaker:
            rendered_text = self.constraints.apply_speech_patterns(ctx.speaker, rendered_text)

        lines_list: List[RenderedLine] = []
        for line in rendered_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            if line.startswith("「") and line.endswith("」"):
                lines_list.append(RenderedLine(speaker=ctx.speaker, text=line, type="dialogue"))
            elif line.startswith("（") and line.endswith("）"):
                lines_list.append(RenderedLine(speaker="", text=line, type="beat"))
            elif line.startswith("——"):
                lines_list.append(RenderedLine(speaker="", text=line, type="action"))
            else:
                lines_list.append(RenderedLine(speaker=ctx.speaker, text=line, type="dialogue"))

        return RenderedDialogue(
            template_id=used_id,
            lines=lines_list,
            raw_text=rendered_text,
            meta={
                "variables": vars_dict,
                "speaker": ctx.speaker,
                "emotion": ctx.emotion,
            },
        )
