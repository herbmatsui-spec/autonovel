"""
src/backend/workflows/adapters/__init__.py - NarrativeState アダプタパッケージ
"""

from src.backend.workflows.adapters.affinity_adapter import update_affinity
from src.backend.workflows.adapters.continuity_adapter import feed_continuity
from src.backend.workflows.adapters.erotic_adapter import update_erotic
from src.backend.workflows.adapters.narrative_adapter import update_narrative
from src.backend.workflows.adapters.quality_adapter import update_quality
from src.backend.workflows.adapters.tension_adapter import update_tension

__all__ = [
    "update_tension",
    "update_affinity",
    "update_quality",
    "update_narrative",
    "update_erotic",
    "feed_continuity",
]
