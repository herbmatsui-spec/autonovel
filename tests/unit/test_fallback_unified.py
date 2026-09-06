"""Unified fallback test suite for all 8 specialist auditors.

Tests that all auditors produce reasonable scores when running in fallback mode (no LLM).
"""

import pytest

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


# Shared test context
SAMPLE_DRAFT = (
    "アリスは城門の前で立ち止まった。なぜ彼女が選ばれたのか、その謎はまだ明かされていない。"
    "空には巨大な暗雲が立ち込め、雷光が閃いた。彼女は覚悟を決めて剣を抜いた。"
    "「行くぞ」と彼女は呟いた。風が彼女の髪を揺らす。運命の歯車が回り始める音がした。"
)

SAMPLE_BIBLE = {
    "characters": [
        {"name": "アリス", "status": "alive", "location": "王都", "faction": "騎士団", "items": ["剣"]},
        {"name": "ボブ", "status": "alive", "location": "王都", "faction": "騎士団"},
    ],
    "locations": [{"name": "王都"}, {"name": "城門"}, {"name": "森"}],
    "items": [{"name": "剣"}, {"name": "盾"}, {"name": "魔法の書"}],
    "factions": [{"name": "騎士団", "members": ["アリス", "ボブ"]}],
    "terms": ["魔法", "剣術", "運命"],
    "meta": {"era": "medieval"},
}

SAMPLE_PLOT = "導入：城門到着 → 展開：葛藤と覚悟 → 転換：剣を抜く → 結び：運命の始まり"

SAMPLE_ILLUSTRATION = "暗雲の下、城門の前で雷光を浴びながら剣を抜くアリス。ドラマチックな陰影、緊迫感。"

SAMPLE_STYLE_DNA = {
    "sample_text": "私は歩く。あなたは走る。剣を握りしめ、前を向く。",
    "first_person": 0.5,
    "polite": 0.0,
}


@pytest.mark.parametrize("auditor_class", [
    ConsistencyAuditor,
    CreativityAuditor,
    ReaderHookAuditor,
    EmotionCurveAuditor,
    StyleAuditor,
    FactualAuditor,
    StructureAuditor,
    MultimodalAuditor,
])
class TestFallbackUnified:
    """Test all auditors in fallback mode produce reasonable scores."""

    @pytest.fixture
    def auditor(self, auditor_class):
        return auditor_class(llm=None)

    @pytest.mark.asyncio
    async def test_fallback_no_llm_returns_reasonable_score(self, auditor, auditor_class):
        """Each auditor should return a score in reasonable range when LLM unavailable."""
        # Build context appropriate for each auditor
        ctx = self._build_context(auditor_class.__name__)

        result = await auditor._safe_audit(ctx)

        # Basic assertions
        assert result.degraded is True, f"{auditor_class.__name__} should be degraded in fallback"
        assert 0.0 <= result.score <= 100.0, f"{auditor_class.__name__} score out of bounds: {result.score}"
        assert result.error is not None and "llm_unavailable" in result.error, \
            f"{auditor_class.__name__} should have llm_unavailable error"

        # Score should not be extreme (not 0 unless empty input, not 100 without reason)
        if ctx.get("draft_text"):
            # StyleAuditor caps at 95, others at 95 or 100
            max_expected = 95.0 if auditor_class.__name__ == "StyleAuditor" else 100.0
            assert 20.0 <= result.score <= max_expected, \
                f"{auditor_class.__name__} fallback score {result.score} outside reasonable range"

    @pytest.mark.asyncio
    async def test_fallback_has_suggestions(self, auditor, auditor_class):
        """Fallback should provide actionable suggestions."""
        ctx = self._build_context(auditor_class.__name__)
        result = await auditor._safe_audit(ctx)

        if ctx.get("draft_text"):  # Only check if there's content to audit
            assert result.suggestions, f"{auditor_class.__name__} should provide suggestions"
            assert all(isinstance(s, str) and len(s) > 0 for s in result.suggestions)

    @pytest.mark.asyncio
    async def test_fallback_has_detailed_feedback(self, auditor, auditor_class):
        """Fallback should include diagnostic feedback."""
        ctx = self._build_context(auditor_class.__name__)
        result = await auditor._safe_audit(ctx)

        assert result.feedback, f"{auditor_class.__name__} should have feedback"
        assert "fallback" in str(result.feedback).lower(), \
            f"{auditor_class.__name__} feedback should indicate fallback mode"

    def _build_context(self, auditor_name: str) -> dict:
        """Build appropriate context for each auditor type."""
        base = {
            "draft_text": SAMPLE_DRAFT,
            "world_bible_snapshot": SAMPLE_BIBLE,
            "plot_tree": SAMPLE_PLOT,
            "illustration_prompts": SAMPLE_ILLUSTRATION,
            "style_dna": SAMPLE_STYLE_DNA,
        }

        # Auditor-specific context adjustments
        if auditor_name == "CreativityAuditor":
            # Creativity doesn't need bible/plot
            return {"draft_text": SAMPLE_DRAFT}
        elif auditor_name == "StyleAuditor":
            return {"draft_text": SAMPLE_DRAFT, "style_dna": SAMPLE_STYLE_DNA}
        elif auditor_name == "MultimodalAuditor":
            return {"draft_text": SAMPLE_DRAFT, "illustration_prompts": SAMPLE_ILLUSTRATION}
        elif auditor_name == "StructureAuditor":
            return {"draft_text": SAMPLE_DRAFT, "plot_tree": SAMPLE_PLOT}
        elif auditor_name in ("ConsistencyAuditor", "FactualAuditor"):
            return {"draft_text": SAMPLE_DRAFT, "world_bible_snapshot": SAMPLE_BIBLE}
        else:
            return base


class TestFallbackEdgeCases:
    """Test fallback behavior with edge case inputs."""

    @pytest.mark.asyncio
    async def test_empty_draft_all_auditors(self):
        """All auditors should handle empty draft gracefully (returns 0 score, not necessarily degraded)."""
        auditors = [
            ConsistencyAuditor(llm=None),
            CreativityAuditor(llm=None),
            ReaderHookAuditor(llm=None),
            EmotionCurveAuditor(llm=None),
            StyleAuditor(llm=None),
            FactualAuditor(llm=None),
            StructureAuditor(llm=None),
            MultimodalAuditor(llm=None),
        ]

        for auditor in auditors:
            ctx = {"draft_text": ""}
            # Add minimal context for those that need it
            if auditor.specialist_name in ("consistency", "factual"):
                ctx["world_bible_snapshot"] = {}
            elif auditor.specialist_name == "structure":
                ctx["plot_tree"] = ""
            elif auditor.specialist_name == "multimodal":
                ctx["illustration_prompts"] = ""
            elif auditor.specialist_name == "style":
                ctx["style_dna"] = {}

            result = await auditor._safe_audit(ctx)
            assert result.score == 0.0, f"{auditor.specialist_name} should score 0 for empty draft"
            # Note: degraded may be False for empty draft (handled in main audit, not fallback)

    @pytest.mark.asyncio
    async def test_minimal_draft_all_auditors(self):
        """All auditors should handle very short draft."""
        auditors = [
            ConsistencyAuditor(llm=None),
            CreativityAuditor(llm=None),
            ReaderHookAuditor(llm=None),
            EmotionCurveAuditor(llm=None),
            StyleAuditor(llm=None),
            FactualAuditor(llm=None),
            StructureAuditor(llm=None),
            MultimodalAuditor(llm=None),
        ]

        short_draft = "アリスは歩いた。"
        for auditor in auditors:
            ctx = {"draft_text": short_draft}
            if auditor.specialist_name in ("consistency", "factual"):
                ctx["world_bible_snapshot"] = SAMPLE_BIBLE
            elif auditor.specialist_name == "structure":
                ctx["plot_tree"] = "アリス、歩く"
            elif auditor.specialist_name == "multimodal":
                ctx["illustration_prompts"] = "アリス、歩く"
            elif auditor.specialist_name == "style":
                ctx["style_dna"] = SAMPLE_STYLE_DNA

            result = await auditor._safe_audit(ctx)
            assert 0.0 <= result.score <= 100.0
            assert result.degraded is True


class TestFallbackScoreDistribution:
    """Test that fallback scores are well-distributed and meaningful."""

    @pytest.mark.asyncio
    async def test_consistency_detects_contradiction(self):
        """Consistency fallback should detect dead character contradiction."""
        auditor = ConsistencyAuditor(llm=None)
        bible = {
            "characters": [{"name": "アリス", "status": "dead"}],
            "locations": [],
            "items": [],
            "factions": [],
            "terms": [],
        }
        ctx = {
            "draft_text": "アリスは走った。アリスは剣を振った。アリスは笑った。",
            "world_bible_snapshot": bible,
        }
        result = await auditor._safe_audit(ctx)
        # Should detect contradiction and score lower
        assert result.score < 70, f"Expected low score for contradiction, got {result.score}"

    @pytest.mark.asyncio
    async def test_factual_detects_anachronism(self):
        """Factual fallback should detect anachronisms in medieval setting."""
        auditor = FactualAuditor(llm=None)
        ctx = {
            "draft_text": "アリスはスマホでインターネットを見ながら剣を振った。",
            "world_bible_snapshot": SAMPLE_BIBLE,
        }
        result = await auditor._safe_audit(ctx)
        assert "スマホ" in str(result.feedback.get("anachronisms_found", []))
        assert "インターネット" in str(result.feedback.get("anachronisms_found", []))
        assert result.score < 70, f"Expected penalty for anachronisms, got {result.score}"

    @pytest.mark.asyncio
    async def test_reader_hook_strong_vs_weak(self):
        """ReaderHook should distinguish strong vs weak hooks."""
        auditor = ReaderHookAuditor(llm=None)

        strong = "なぜ彼女は死んだのか？謎が深まる。突然、扉が開いた！"
        weak = "アリスは歩いた。空は青かった。鳥が鳴いていた。"

        result_strong = await auditor._safe_audit({"draft_text": strong})
        result_weak = await auditor._safe_audit({"draft_text": weak})

        assert result_strong.score > result_weak.score, \
            f"Strong hooks ({result_strong.score}) should score higher than weak ({result_weak.score})"

    @pytest.mark.asyncio
    async def test_multimodal_triple_layer_matching(self):
        """Multimodal should use three-layer matching."""
        auditor = MultimodalAuditor(llm=None)

        draft = "アリスは剣を持って笑った。ボブは盾を構えて怒った。"
        # Use natural language for illustration prompts so triple extraction works
        illust_match = "アリスが剣を持って笑っている。ドラマチックな光。"
        illust_mismatch = "チャーリーが杖を持って泣いている。穏やかな光。"

        result_match = await auditor._safe_audit({
            "draft_text": draft,
            "illustration_prompts": illust_match,
        })
        result_mismatch = await auditor._safe_audit({
            "draft_text": draft,
            "illustration_prompts": illust_mismatch,
        })

        assert result_match.score > result_mismatch.score, \
            f"Match ({result_match.score}) should score higher than mismatch ({result_mismatch.score})"
        # Check that triple-layer matching was used (not bigram fallback)
        assert "char_jaccard" in result_match.feedback
        # The triple extraction may not perfectly capture characters from short prompts,
        # but the overall score should still differentiate match vs mismatch


if __name__ == "__main__":
    pytest.main([__file__, "-v"])