"""
Subtext Templates Package: Jinja2-based subtext template library and matching engine (PLAN_Y2).
"""

from src.narrative.subtext_templates.constraints import CharacterConstraints
from src.narrative.subtext_templates.loader import TemplateLoader
from src.narrative.subtext_templates.matcher import ContextMatcher
from src.narrative.subtext_templates.models import (
    RenderedDialogue,
    RenderedLine,
    TemplateCandidate,
    TemplateMetadata,
)
from src.narrative.subtext_templates.renderer import TemplateRenderer

__all__ = [
    "TemplateLoader",
    "ContextMatcher",
    "TemplateRenderer",
    "CharacterConstraints",
    "TemplateMetadata",
    "TemplateCandidate",
    "RenderedLine",
    "RenderedDialogue",
]
