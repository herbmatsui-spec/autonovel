"""
ContextMatcher: Matches dialogue context against subtext templates (PLAN_Y2 Step 4, 15, 17).
"""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from src.narrative.subtext_engine.models import SubtextContext
from src.narrative.subtext_templates.constraints import CharacterConstraints
from src.narrative.subtext_templates.models import TemplateCandidate

logger = logging.getLogger("narrative.subtext_templates.matcher")


class ContextMatcher:
    """Matches contextual conditions to candidate templates with weighting and history awareness."""

    def __init__(
        self,
        scene_config_path: Optional[str | Path] = None,
        constraints: Optional[CharacterConstraints] = None,
    ) -> None:
        self.scene_config_path = Path(scene_config_path or "config/scene_context.yaml")
        self.constraints = constraints or CharacterConstraints()
        self.genre_weights: Dict[str, Dict[str, float]] = {}
        self.tone_weights: Dict[str, Dict[str, float]] = {}
        self._load_scene_weights()

    def _load_scene_weights(self) -> None:
        if self.scene_config_path.exists():
            try:
                data = yaml.safe_load(self.scene_config_path.read_text(encoding="utf-8")) or {}
                self.genre_weights = data.get("genres", {})
                self.tone_weights = data.get("tones", {})
            except Exception as e:
                logger.warning(f"Failed to load scene context from {self.scene_config_path}: {e}")

    def score_candidate(
        self, candidate: TemplateCandidate, context: SubtextContext
    ) -> float:
        meta = candidate.metadata
        req_ctx = meta.context or {}
        score = float(meta.weight)

        # Match emotion
        req_emotions = req_ctx.get("emotion")
        if req_emotions:
            if isinstance(req_emotions, str):
                req_emotions = [req_emotions]
            if context.emotion and context.emotion != "neutral":
                if context.emotion in req_emotions:
                    score *= 1.5
                else:
                    return 0.0  # Incompatible emotion

        # Match power dynamic
        req_power = req_ctx.get("power_dynamic")
        if req_power:
            if isinstance(req_power, str):
                req_power = [req_power]
            if context.power_dynamic in req_power:
                score *= 1.3

        # Match relationship
        req_rel = req_ctx.get("relationship")
        if req_rel:
            if isinstance(req_rel, str):
                req_rel = [req_rel]
            if context.relationship in req_rel:
                score *= 1.3

        # Match intensity
        req_intensity = req_ctx.get("intensity")
        if req_intensity:
            if isinstance(req_intensity, str):
                req_intensity = [req_intensity]
            if context.intensity in req_intensity:
                score *= 1.2

        # Step 17: Apply scene genre & tone weights
        cat = meta.category or meta.id.split(".")[0]
        if context.genre in self.genre_weights:
            multiplier = self.genre_weights[context.genre].get(cat, 1.0)
            score *= multiplier
        if context.tone in self.tone_weights:
            multiplier = self.tone_weights[context.tone].get(cat, 1.0)
            score *= multiplier

        # Step 15: History penalty if used recently in last 3 turns
        if context.history_summary:
            recent_ids = context.history_summary[-3:]
            if candidate.id in recent_ids:
                score *= 0.2

        return score

    def match(
        self,
        candidates: List[TemplateCandidate],
        context: SubtextContext,
    ) -> List[TemplateCandidate]:
        """Filters and scores template candidates given the context."""
        matched: List[TemplateCandidate] = []

        for candidate in candidates:
            # Step 16: Check character constraints
            if context.speaker and not self.constraints.is_template_allowed(
                context.speaker, candidate.metadata.tags
            ):
                continue

            score = self.score_candidate(candidate, context)
            if score > 0:
                scored = candidate.model_copy()
                scored.score = score
                matched.append(scored)

        if not matched:
            for candidate in candidates:
                req_emotions = (candidate.metadata.context or {}).get("emotion")
                if not req_emotions:
                    scored = candidate.model_copy()
                    scored.score = float(candidate.metadata.weight)
                    matched.append(scored)

        # Sort: final templates first, then score descending
        matched.sort(key=lambda c: (c.metadata.final, c.score), reverse=True)
        return matched

    def select(
        self,
        candidates: List[TemplateCandidate],
        context: SubtextContext,
        seed: Optional[int] = None,
    ) -> Optional[TemplateCandidate]:
        """Selects the best template candidate deterministically using seeded weighting."""
        matches = self.match(candidates, context)
        if not matches:
            return None

        # If highest candidate has final=True, return it directly
        if matches[0].metadata.final:
            return matches[0]

        # Deterministic seed calculation
        calc_seed = seed
        if calc_seed is None:
            calc_seed = hash(f"{context.scene_id}_{context.turn_index}_{context.speaker}") & 0xFFFFFFFF

        rnd = random.Random(calc_seed)
        weights = [max(0.1, m.score) for m in matches]
        selected = rnd.choices(matches, weights=weights, k=1)[0]
        return selected
