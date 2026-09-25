"""Phase 1 Debt Clearance and Stabilization Comprehensive Regression Suite (Step 35)."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.content_processor import ContentProcessor
from src.services.narrative_scoring_service import NarrativeScoringService
from src.services.llm.gemini_adapter import GeminiAdapter
from src.services.audio.speaker_mapper import assign_speaker_id
from src.config.emotional_hook_vocabulary import EMOTIONAL_HOOKS
from src.agents.orchestrator import Orchestrator, CyclicDependencyError


def test_content_processor_normalization():
    """Verify NFKC normalization, HTML sanitization, and punctuation alignment."""
    cp = ContentProcessor()
    raw = "<script>alert('xss');</script>ｱｲｳｴｵ １２３  … ―"
    cleaned = cp.sanitize(raw)
    assert "アイウエオ" in cleaned
    assert "123" in cleaned
    assert "……" in cleaned
    assert "――" in cleaned
    assert "<script>" not in cleaned


@pytest.mark.asyncio
async def test_narrative_scoring_service_fallback():
    """Verify NarrativeScoringService provides sensible fallback when LLM is unavailable."""
    nss = NarrativeScoringService(llm=None, prompt_manager=None)
    result = await nss.score("第1章 ドラフト本文")
    assert result["score"] >= 70.0
    assert "feedback" in result


def test_speaker_mapper_default_character():
    """Verify assign_speaker_id returns valid VOICEVOX ID."""
    speaker_id = assign_speaker_id("その他・一般キャラクター")
    assert isinstance(speaker_id, int)
    assert speaker_id >= 0


def test_emotional_hook_vocabulary_completeness():
    """Verify all critical emotional hooks exist in vocabulary."""
    assert "despair_to_hope" in EMOTIONAL_HOOKS
    assert "tension_relief" in EMOTIONAL_HOOKS


def test_orchestrator_cyclic_dependency_exception():
    """Verify CyclicDependencyError is raised on circular manifests."""
    orch = Orchestrator(nodes={})
    manifest = [
        {"name": "A", "depends_on": ["B"], "runs_after": [], "runs_before": []},
        {"name": "B", "depends_on": ["A"], "runs_after": [], "runs_before": []},
    ]
    available = {"A": MagicMock(), "B": MagicMock()}
    with pytest.raises((RuntimeError, ValueError, CyclicDependencyError)):
        orch.build_execution_order(manifest, available)
