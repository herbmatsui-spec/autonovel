"""
GenerationPipeline: Unified narrative generation and subtext processing pipeline.
Supports subtext_mode: 'rule' | 'template' | 'token' | 'hybrid' | 'off'.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Dict, List, Optional

from src.narrative.subtext_engine.engine import SubtextEngine
from src.narrative.subtext_engine.models import DialogueBlock, SubtextContext
from src.narrative.subtext_templates.matcher import ContextMatcher
from src.narrative.subtext_templates.renderer import TemplateRenderer
from src.narrative.subtext_tokens.formatter import DialogueFormatter

logger = logging.getLogger("pipeline.generation")


class GenerationPipeline:
    """Orchestrates LLM generation hooks and subtext processing engines."""

    def __init__(
        self,
        subtext_mode: str = "hybrid",
        engine: Optional[SubtextEngine] = None,
        renderer: Optional[TemplateRenderer] = None,
        formatter: Optional[DialogueFormatter] = None,
    ) -> None:
        self.subtext_mode = subtext_mode.lower()
        self.engine = engine or SubtextEngine.create_default()
        self.renderer = renderer or TemplateRenderer()
        self.formatter = formatter or DialogueFormatter()
        self.post_process_hooks: List[Callable[[str, Optional[SubtextContext]], str]] = []

    def set_mode(self, mode: str) -> None:
        """Dynamically switches subtext processing mode."""
        valid_modes = {"rule", "template", "token", "hybrid", "off"}
        if mode.lower() not in valid_modes:
            raise ValueError(f"Invalid mode '{mode}'. Choose from {valid_modes}")
        self.subtext_mode = mode.lower()

    def process_text(
        self,
        text: str,
        context: Optional[SubtextContext] = None,
        seed: Optional[int] = None,
    ) -> str:
        """Processes raw dialogue text through subtext engines according to current mode."""
        if self.subtext_mode == "off":
            return text

        current = text

        # 1. Token Expansion & Formatting (Token mode or Hybrid mode)
        if self.subtext_mode in ["token", "hybrid"]:
            current = self.formatter.post_process_dialogue(current, context=context, seed=seed)

        # 2. Deterministic Rule Rewrite (Rule mode or Hybrid mode)
        if self.subtext_mode in ["rule", "hybrid"]:
            lines = [ln for ln in current.split("\n") if ln.strip()]
            speaker = context.speaker if context else ""
            block = DialogueBlock(speaker=speaker, lines=lines)
            processed_blocks = self.engine.process([block], context=context)
            if processed_blocks:
                current = processed_blocks[0].raw_text()

        # 3. Custom post_process hooks (Step 15 of PLAN_Y1)
        for hook in self.post_process_hooks:
            try:
                current = hook(current, context)
            except Exception as e:
                logger.warning(f"Error in post_process hook: {e}")

        return current

    def render_template(
        self,
        template_id_or_auto: str = "auto",
        context: Optional[SubtextContext] = None,
        variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Renders dialogue from template library (Template mode)."""
        ctx = context or SubtextContext()
        if template_id_or_auto == "auto":
            candidates = list(self.renderer.loader.load_all().values())
            matcher = ContextMatcher()
            selected = matcher.select(candidates, ctx)
            candidate_arg = selected or "fallback.generic_subtext"
        else:
            candidate_arg = template_id_or_auto

        res = self.renderer.render(candidate_arg, variables=variables, context=ctx)
        return res.raw_text
