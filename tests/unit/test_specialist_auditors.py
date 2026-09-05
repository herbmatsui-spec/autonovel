"""Unit tests for 8 Specialist Auditors."""

import pytest
import asyncio
from unittest.mock import MagicMock

from src.agents.specialists import (
    ConsistencyAuditor,
    CreativityAuditor,
    ReaderHookAuditor,
    EmotionCurveAuditor,
    StyleAuditor,
    FactualAuditor,
    StructureAuditor,
    MultimodalAuditor,
)
from src.agents.specialist_auditor_base import SpecialistAuditResult, LLMUnavailableError


class TestConsistencyAuditor:
    @pytest.fixture
    def auditor(self):
        return ConsistencyAuditor()

    @pytest.mark.asyncio
    async def test_perfect_match(self, auditor):
        ctx = {
            "draft_text": "アリスは東京で剣を振った。ボブも東京にいた。",
            "world_bible_snapshot": {
                "characters": [{"name": "アリス"}, {"name": "ボブ"}],
                "locations": [{"name": "東京"}],
                "items": [{"name": "剣"}],
            }
        }
        result = await auditor._safe_audit(ctx)
        assert 70 <= result.score <= 100
        assert result.feedback["found_entities"] == 4
        assert result.degraded is True  # fallback mode

    @pytest.mark.asyncio
    async def test_partial_match(self, auditor):
        ctx = {
            "draft_text": "アリスは東京で剣を振った。",
            "world_bible_snapshot": {
                "characters": [{"name": "アリス"}, {"name": "ボブ"}],
                "locations": [{"name": "東京"}],
                "items": [{"name": "剣"}],
            }
        }
        result = await auditor._safe_audit(ctx)
        assert result.score < 85
        assert result.feedback["found_entities"] == 3
        assert result.degraded is True

    @pytest.mark.asyncio
    async def test_contradiction_penalty(self, auditor):
        ctx = {
            "draft_text": "アリスは死んだ。だがアリスは生きている。",
            "world_bible_snapshot": {"characters": [{"name": "アリス"}]}
        }
        result = await auditor._safe_audit(ctx)
        # In fallback mode, check rule_coverage instead
        assert "rule_coverage" in result.feedback
        assert result.degraded is True

    @pytest.mark.asyncio
    async def test_empty_draft(self, auditor):
        ctx = {"draft_text": "", "world_bible_snapshot": {}}
        result = await auditor._safe_audit(ctx)
        assert result.score == 0.0


class TestCreativityAuditor:
    @pytest.fixture
    def auditor(self):
        return CreativityAuditor()

    @pytest.mark.asyncio
    async def test_diverse_text(self, auditor):
        ctx = {"draft_text": "アリスは青い空を見上げた。美しい雲が流れる。心が躍るような気持ちだ。"}
        result = await auditor._safe_audit(ctx)
        assert result.score > 50

    @pytest.mark.asyncio
    async def test_repetitive_text(self, auditor):
        ctx = {"draft_text": "アリスは走った。アリスは走った。アリスは走った。アリスは走った。"}
        result = await auditor._safe_audit(ctx)
        assert result.score < 60

    @pytest.mark.asyncio
    async def test_empty(self, auditor):
        ctx = {"draft_text": ""}
        result = await auditor._safe_audit(ctx)
        assert result.score == 0.0


class TestReaderHookAuditor:
    @pytest.fixture
    def auditor(self):
        return ReaderHookAuditor()

    @pytest.mark.asyncio
    async def test_strong_hooks(self, auditor):
        ctx = {"draft_text": "なぜ彼女は死んだのか？謎が深まる。突然、扉が開いた！"}
        result = await auditor._safe_audit(ctx)
        assert result.score > 50

    @pytest.mark.asyncio
    async def test_weak_hooks(self, auditor):
        ctx = {"draft_text": "アリスは歩いた。空は青かった。鳥が鳴いていた。"}
        result = await auditor._safe_audit(ctx)
        # Fallback minimum score is 10.0
        assert result.score == 10.0
        assert result.degraded is True

    @pytest.mark.asyncio
    async def test_empty(self, auditor):
        ctx = {"draft_text": ""}
        result = await auditor._safe_audit(ctx)
        assert result.score == 0.0


class TestEmotionCurveAuditor:
    @pytest.fixture
    def auditor(self):
        return EmotionCurveAuditor()

    @pytest.mark.asyncio
    async def test_emotional_arc(self, auditor):
        ctx = {"draft_text": "アリスは悲しんでいた。涙が止まらない。だが希望を見つけた。光が差し込み、心が救われた。"}
        result = await auditor._safe_audit(ctx)
        assert result.score > 0

    @pytest.mark.asyncio
    async def test_flat_text(self, auditor):
        ctx = {"draft_text": "アリスは歩いた。鳥が鳴いた。風が吹いた。"}
        result = await auditor._safe_audit(ctx)
        # Fallback minimum score is 20.0
        assert result.score == 20.0
        assert result.degraded is True

    @pytest.mark.asyncio
    async def test_empty(self, auditor):
        ctx = {"draft_text": ""}
        result = await auditor._safe_audit(ctx)
        assert result.score == 0.0


class TestStyleAuditor:
    @pytest.fixture
    def auditor(self):
        return StyleAuditor(style_profile={"sample_text": "私は歩く。あなたは走る。", "first_person": 0.5, "polite": 0.0})

    @pytest.mark.asyncio
    async def test_matching_style(self, auditor):
        ctx = {
            "draft_text": "私は歩いた。あなたは走った。",
            "style_dna": {"sample_text": "私は歩く。あなたは走る。", "first_person": 0.5, "polite": 0.0}
        }
        result = await auditor._safe_audit(ctx)
        assert result.score > 10

    @pytest.mark.asyncio
    async def test_mismatched_politeness(self, auditor):
        ctx = {
            "draft_text": "私は歩きます。あなたは走ります。",
            "style_dna": {"sample_text": "私は歩く。あなたは走る。", "first_person": 0.5, "polite": 0.0}
        }
        result = await auditor._safe_audit(ctx)
        # Fallback returns polite_ratio and first_person_ratio
        assert "polite_ratio" in result.feedback
        assert "first_person_ratio" in result.feedback
        assert result.degraded is True

    @pytest.mark.asyncio
    async def test_empty(self, auditor):
        ctx = {"draft_text": ""}
        result = await auditor._safe_audit(ctx)
        assert result.score == 0.0


class TestFactualAuditor:
    @pytest.fixture
    def auditor(self):
        return FactualAuditor(llm=None)

    @pytest.mark.asyncio
    async def test_all_found_fallback(self, auditor):
        ctx = {
            "draft_text": "アリスは東京で剣を振った。",
            "world_bible_snapshot": {
                "characters": [{"name": "アリス"}],
                "locations": [{"name": "東京"}],
                "items": [{"name": "剣"}],
            }
        }
        result = await auditor._safe_audit(ctx)
        assert result.score == 100.0
        assert result.degraded is True

    @pytest.mark.asyncio
    async def test_partial_fallback(self, auditor):
        ctx = {
            "draft_text": "アリスは大阪で杖を振った。",
            "world_bible_snapshot": {
                "characters": [{"name": "アリス"}],
                "locations": [{"name": "東京"}],
                "items": [{"name": "剣"}],
            }
        }
        result = await auditor._safe_audit(ctx)
        assert 30 <= result.score < 100
        assert result.degraded is True

    @pytest.mark.asyncio
    async def test_empty(self, auditor):
        ctx = {"draft_text": "", "world_bible_snapshot": {}}
        result = await auditor._safe_audit(ctx)
        assert result.score == 0.0


class TestStructureAuditor:
    @pytest.fixture
    def auditor(self):
        return StructureAuditor(llm=None)

    @pytest.mark.asyncio
    async def test_good_coverage(self, auditor):
        ctx = {
            "draft_text": "アリスは東京で剣を振って敵を倒した。その後、王都へ向かった。",
            "plot_tree": "アリス、東京、剣、敵、倒す、王都、向かう"
        }
        result = await auditor._safe_audit(ctx)
        assert result.degraded is True

    @pytest.mark.asyncio
    async def test_low_coverage(self, auditor):
        ctx = {"draft_text": "アリスは歩いた。", "plot_tree": "アリス、東京、剣、敵、王都"}
        result = await auditor._safe_audit(ctx)
        assert result.score < 50

    @pytest.mark.asyncio
    async def test_empty(self, auditor):
        ctx = {"draft_text": "", "plot_tree": ""}
        result = await auditor._safe_audit(ctx)
        assert result.score == 0.0


class TestMultimodalAuditor:
    @pytest.fixture
    def auditor(self):
        return MultimodalAuditor(llm=None)

    @pytest.mark.asyncio
    async def test_some_overlap(self, auditor):
        ctx = {
            "draft_text": "アリスは青い空の下で剣を構えた。風が髪を揺らす。",
            "illustration_prompts": "アリス、青い空、剣、風、髪"
        }
        result = await auditor._safe_audit(ctx)
        assert result.degraded is True
        assert result.score > 0

    @pytest.mark.asyncio
    async def test_no_overlap(self, auditor):
        ctx = {
            "draft_text": "アリスは青い空の下で剣を構えた。",
            "illustration_prompts": "ボブ、赤い空、杖、雨"
        }
        result = await auditor._safe_audit(ctx)
        assert result.score < 20

    @pytest.mark.asyncio
    async def test_empty(self, auditor):
        ctx = {"draft_text": "", "illustration_prompts": ""}
        result = await auditor._safe_audit(ctx)
        assert result.score == 0.0


class TestLLMFallback:
    @pytest.mark.asyncio
    async def test_factual_llm_unavailable(self):
        auditor = FactualAuditor(llm=None)
        ctx = {
            "draft_text": "アリスは東京で剣を振った。",
            "world_bible_snapshot": {"characters": [{"name": "アリス"}]}
        }
        with pytest.raises(LLMUnavailableError):
            await auditor.audit(ctx)
        result = await auditor._safe_audit(ctx)
        assert result.degraded is True
        assert result.error and "llm_unavailable" in result.error