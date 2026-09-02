"""Extended unit tests for src/services/writing_services.py - Writing generation services."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.services.writing_services import (
    WritingGenerationContext,
    GenerationLoopManager,
)


class TestWritingGenerationContext:
    """Extended tests for WritingGenerationContext."""

    def test_defaults(self):
        """Test default values."""
        ctx = WritingGenerationContext()
        assert ctx.style_key == "style_web_standard"
        assert ctx.target_word_count == 2000
        assert ctx.enable_polishing is True
        assert ctx.prose_sample == ""
        assert ctx.plot is None

    def test_build_sys_inst_with_all_fields(self):
        """Test sys_inst building with all fields."""
        ctx = WritingGenerationContext(
            sys_inst="Base instruction",
            pov_instruction="POV instruction",
            feedback_patch="Feedback patch",
        )
        result = ctx.build_sys_inst()
        assert "Base instruction" in result
        assert "POV instruction" in result
        assert "【🚨自己評価フィードバックパッチ】" in result
        assert "Feedback patch" in result

    def test_build_sys_inst_minimal(self):
        """Test sys_inst with only base instruction."""
        ctx = WritingGenerationContext(sys_inst="Only base")
        assert ctx.build_sys_inst() == "Only base"

    def test_build_sys_inst_no_feedback(self):
        """Test sys_inst without feedback patch."""
        ctx = WritingGenerationContext(
            sys_inst="Base",
            pov_instruction="POV",
        )
        result = ctx.build_sys_inst()
        assert "Base" in result
        assert "POV" in result
        assert "自己評価フィードバックパッチ" not in result

    def test_build_fw_prompt_with_all_fields(self):
        """Test fw_prompt building with all fields."""
        ctx = WritingGenerationContext(
            fw_prompt="Base prompt",
            pov_instruction="POV instruction",
            expanded_beats="Beat 1\nBeat 2",
        )
        result = ctx.build_fw_prompt("Suffix text")
        assert "Base prompt" in result
        assert "POV instruction" in result
        assert "物理動作ビート分解" in result
        assert "Beat 1" in result
        assert "Beat 2" in result
        assert "Suffix text" in result

    def test_build_fw_prompt_minimal(self):
        """Test fw_prompt with minimal fields."""
        ctx = WritingGenerationContext(fw_prompt="Only prompt")
        result = ctx.build_fw_prompt()
        assert result == "Only prompt"

    def test_build_fw_prompt_no_beats(self):
        """Test fw_prompt without expanded beats."""
        ctx = WritingGenerationContext(
            fw_prompt="Base",
            pov_instruction="POV",
        )
        result = ctx.build_fw_prompt()
        assert "物理動作ビート分解" not in result


class TestGenerationLoopManager:
    """Tests for GenerationLoopManager."""

    def setup_method(self):
        self.mock_repo = MagicMock()
        self.mock_llm = MagicMock()
        self.mock_pm = MagicMock()
        self.mock_critique = MagicMock()
        self.mock_narrative = MagicMock()
        self.mock_config = MagicMock()

        self.manager = GenerationLoopManager(
            repo=self.mock_repo,
            llm=self.mock_llm,
            pm=self.mock_pm,
            critique=self.mock_critique,
            narrative=self.mock_narrative,
            config=self.mock_config,
        )

    def test_init(self):
        """Test initialization."""
        assert self.manager.repo == self.mock_repo
        assert self.manager.llm == self.mock_llm
        assert self.manager.pm == self.mock_pm
        assert self.manager.critique == self.mock_critique
        assert self.manager.narrative == self.mock_narrative
        assert self.manager.config == self.mock_config

    @pytest.mark.asyncio
    async def test_phase_prepare_context(self):
        """Test _phase_prepare_context."""
        mock_ctx = MagicMock()
        mock_ctx.current_tension = 50
        mock_ctx.plot = MagicMock()
        mock_ctx.plot.is_catharsis = False
        mock_ctx.plot.summary = ""
        mock_ctx.plot.detailed_blueprint = ""
        mock_ctx.book = MagicMock()
        mock_ctx.book.style_dna = '{"mode": "style_web_standard"}'
        mock_ctx.book.target_eps = 50
        mock_ctx.prose_samples = ["sample prose"]
        mock_ctx.target_word_count = 2000
        mock_ctx.engine_key = "test_engine"

        mock_reporter = MagicMock()

        with patch("src.services.writing_services.ProjectContext.get_setting", side_effect=lambda k, d=None: {
            "actor_critic_max_iterations": 2,
            "fail_fast_mode": False,
        }.get(k, d)):
            gen_ctx, should_dogfeed, should_heavy_audit, should_beat_decompose, ncs_score = \
                await self.manager._phase_prepare_context(1, mock_ctx, "sys", "fw", False, mock_reporter)

        assert isinstance(gen_ctx, WritingGenerationContext)
        assert gen_ctx.sys_inst == "sys"
        assert gen_ctx.fw_prompt == "fw"
        assert gen_ctx.target_word_count == 2000
        assert gen_ctx.prose_sample == "sample prose"

    @pytest.mark.asyncio
    async def test_phase_prepare_context_catharsis(self):
        """Test _phase_prepare_context with catharsis episode."""
        mock_ctx = MagicMock()
        mock_ctx.current_tension = 90
        mock_ctx.plot = MagicMock()
        mock_ctx.plot.is_catharsis = True
        mock_ctx.plot.summary = ""
        mock_ctx.plot.detailed_blueprint = ""
        mock_ctx.book = MagicMock()
        mock_ctx.book.style_dna = '{"mode": "style_web_standard"}'
        mock_ctx.book.target_eps = 50
        mock_ctx.prose_samples = []
        mock_ctx.target_word_count = 2000
        mock_ctx.engine_key = "test_engine"

        mock_reporter = MagicMock()

        with patch("src.services.writing_services.ProjectContext.get_setting", return_value=2):
            gen_ctx, should_dogfeed, should_heavy_audit, should_beat_decompose, ncs_score = \
                await self.manager._phase_prepare_context(1, mock_ctx, "sys", "fw", False, mock_reporter)

        assert ncs_score >= 50  # catharsis adds 50
        assert "視点変更" in gen_ctx.pov_instruction or "幕間" in gen_ctx.pov_instruction

    @pytest.mark.asyncio
    async def test_calculate_ncs_score(self):
        """Test _calculate_ncs_score."""
        mock_ctx = MagicMock()
        mock_ctx.plot = MagicMock()
        mock_ctx.plot.is_catharsis = True
        mock_ctx.plot.summary = "climax battle"
        mock_ctx.plot.detailed_blueprint = "resolution"
        mock_ctx.book = MagicMock()
        mock_ctx.book.target_eps = 10

        with patch("src.services.writing_services.AUDIT_TRIGGER_KEYWORDS", ["climax", "battle"]):
            score = self.manager._calculate_ncs_score(1, mock_ctx)

        assert score >= 80  # 50 (catharsis) + 30 (keywords)

    @pytest.mark.asyncio
    async def test_calculate_ncs_score_first_episode(self):
        """Test NCS score for first episode."""
        mock_ctx = MagicMock()
        mock_ctx.plot = MagicMock()
        mock_ctx.plot.is_catharsis = False
        mock_ctx.plot.summary = ""
        mock_ctx.plot.detailed_blueprint = ""
        mock_ctx.book = MagicMock()
        mock_ctx.book.target_eps = 50

        score = self.manager._calculate_ncs_score(1, mock_ctx)
        assert score >= 30  # first episode bonus

    @pytest.mark.asyncio
    async def test_calculate_ncs_score_last_episodes(self):
        """Test NCS score for last episodes."""
        mock_ctx = MagicMock()
        mock_ctx.plot = MagicMock()
        mock_ctx.plot.is_catharsis = False
        mock_ctx.plot.summary = ""
        mock_ctx.plot.detailed_blueprint = ""
        mock_ctx.book = MagicMock()
        mock_ctx.book.target_eps = 10

        score = self.manager._calculate_ncs_score(9, mock_ctx)  # 9 out of 10
        assert score >= 30  # near end bonus

    @pytest.mark.asyncio
    async def test_expand_scene_beats(self):
        """Test _expand_scene_beats."""
        mock_reporter = MagicMock()
        self.mock_pm.build_beat_expansion_prompt = AsyncMock(return_value="beat prompt")
        self.mock_llm.generate_json = AsyncMock()
        mock_result = MagicMock()
        mock_result.unwrap_or.return_value = ({"beats": [{"beat_num": 1, "physical_action": "Action", "sensory_tags": ["visual"], "emotion_phase": "tense", "word_budget": 200}]}, "")
        self.mock_llm.generate_json.return_value = mock_result

        with patch("src.services.writing_services.ProjectContext.get_setting", return_value="model_name"):
            result = await self.manager._expand_scene_beats(1, "blueprint", 0.7, mock_reporter)

        assert "ビート1" in result
        assert "Action" in result
        assert "五感: visual" in result
        assert "フェーズ: tense" in result
        assert "目標文字数: 200字" in result

    @pytest.mark.asyncio
    async def test_expand_scene_beats_fallback(self):
        """Test _expand_scene_beats fallback to content."""
        mock_reporter = MagicMock()
        self.mock_pm.build_beat_expansion_prompt = AsyncMock(return_value="beat prompt")
        self.mock_llm.generate_json = AsyncMock()
        mock_result = MagicMock()
        mock_result.unwrap_or.return_value = ({}, "fallback content")
        self.mock_llm.generate_json.return_value = mock_result

        with patch("src.services.writing_services.ProjectContext.get_setting", return_value="model_name"):
            result = await self.manager._expand_scene_beats(1, "blueprint", 0.7, mock_reporter)

        assert result == "fallback content"

    @pytest.mark.asyncio
    async def test_draft_episode_parts(self):
        """Test _draft_episode_parts."""
        mock_reporter = MagicMock()
        gen_ctx = WritingGenerationContext(
            sys_inst="sys",
            fw_prompt="fw",
            target_word_count=2000,
        )

        self.mock_llm.generate_text = AsyncMock()
        # First call - part 1
        mock_res1 = MagicMock()
        mock_res1.success = True
        mock_res1.story_content = "Part 1 content"
        # Second call - part 2
        mock_res2 = MagicMock()
        mock_res2.success = True
        mock_res2.story_content = "Part 2 content"
        self.mock_llm.generate_text.side_effect = [mock_res1, mock_res2]

        result = await self.manager._draft_episode_parts(1, gen_ctx, 0.7, mock_reporter)

        assert "Part 1 content" in result
        assert "Part 2 content" in result
        assert self.mock_llm.generate_text.call_count == 2

    @pytest.mark.asyncio
    async def test_draft_episode_parts_failure(self):
        """Test _draft_episode_parts failure handling."""
        mock_reporter = MagicMock()
        gen_ctx = WritingGenerationContext(sys_inst="sys", fw_prompt="fw")

        self.mock_llm.generate_text = AsyncMock()
        mock_res = MagicMock()
        mock_res.success = False
        mock_res.story_content = ""
        self.mock_llm.generate_text.return_value = mock_res

        result = await self.manager._draft_episode_parts(1, gen_ctx, 0.7, mock_reporter)

        assert result == ""

    @pytest.mark.asyncio
    async def test_polishing_pass(self):
        """Test _polishing_pass."""
        mock_reporter = MagicMock()
        gen_ctx = WritingGenerationContext(
            target_word_count=2000,
            style_key="style_web_standard",
            prose_sample="sample",
            plot=MagicMock(),
        )
        gen_ctx.plot.model_dump = MagicMock(return_value={})

        self.mock_pm.build_polishing_prompt = AsyncMock(return_value="polish prompt")
        self.mock_llm.generate_text = AsyncMock()
        mock_res = MagicMock()
        mock_res.success = True
        mock_res.story_content = "Polished content that is longer than draft"
        self.mock_llm.generate_text.return_value = mock_res

        with patch("src.services.writing_services.ProjectContext.get_setting", side_effect=lambda k, d=None: {
            "draft_polish_enabled": True,
            "polishing_min_content_ratio": 0.5,
        }.get(k, d)):
            result = await self.manager._polishing_pass(1, "Draft content", gen_ctx, 0.7, mock_reporter, use_beat_rules=True)

        assert result == "Polished content that is longer than draft"

    @pytest.mark.asyncio
    async def test_polishing_pass_fallback(self):
        """Test _polishing_pass falls back to draft on failure."""
        mock_reporter = MagicMock()
        gen_ctx = WritingGenerationContext(target_word_count=2000)

        self.mock_pm.build_polishing_prompt = AsyncMock(return_value="polish prompt")
        self.mock_llm.generate_text = AsyncMock()
        mock_res = MagicMock()
        mock_res.success = False
        self.mock_llm.generate_text.return_value = mock_res

        with patch("src.services.writing_services.ProjectContext.get_setting", return_value=True):
            result = await self.manager._polishing_pass(1, "Original draft", gen_ctx, 0.7, mock_reporter)

        assert result == "Original draft"

    @pytest.mark.asyncio
    async def test_extract_episode_metadata(self):
        """Test _extract_episode_metadata."""
        self.mock_llm.generate_json = AsyncMock()
        mock_res = MagicMock()
        mock_res.success = True
        mock_res.metadata = {"title": "Ep 1", "summary": "Summary"}
        self.mock_llm.generate_json.return_value = mock_res

        with patch("src.services.writing_services.ProjectContext.get_setting", return_value="model_name"):
            result = await self.manager._extract_episode_metadata(1, "content", "blueprint", 0.7)

        assert result["title"] == "Ep 1"
        assert result["summary"] == "Summary"

    @pytest.mark.asyncio
    async def test_extract_episode_metadata_failure(self):
        """Test _extract_episode_metadata on failure."""
        self.mock_llm.generate_json = AsyncMock()
        mock_res = MagicMock()
        mock_res.success = False
        self.mock_llm.generate_json.return_value = mock_res

        result = await self.manager._extract_episode_metadata(1, "content", "blueprint", 0.7)
        assert result == {}

    @pytest.mark.asyncio
    async def test_run_causality_audits(self):
        """Test _run_causality_audits."""
        mock_ctx = MagicMock()
        mock_ctx.bible = MagicMock()
        mock_ctx.bible.settings = '{"active_constraints": []}'

        mock_monitor = MagicMock()
        mock_monitor.audit_setting_causality = AsyncMock(return_value=(True, "", []))
        mock_monitor.run_constraint_unit_tests = AsyncMock(return_value=(True, []))

        with patch("src.services.writing_services.AUDIT_TRIGGER_KEYWORDS", ["test"]):
            is_ok, reason, failures = await self.manager._run_causality_audits(
                1, mock_ctx, "content with test keyword", "blueprint", True, mock_monitor
            )

        assert is_ok is True
        assert reason == ""
        assert failures == []

    @pytest.mark.asyncio
    async def test_run_causality_audits_with_failures(self):
        """Test _run_causality_audits with failures."""
        mock_ctx = MagicMock()
        mock_ctx.bible = MagicMock()
        mock_ctx.bible.settings = '{"active_constraints": [{"constraint": "test"}]}'

        mock_monitor = MagicMock()
        mock_monitor.audit_setting_causality = AsyncMock(return_value=(False, "Causality failed", [{"rule": "test", "gap": "gap", "fragment": "frag"}]))
        mock_monitor.run_constraint_unit_tests = AsyncMock(return_value=(False, [{"constraint_index": 0, "reason": "violation", "violating_snippet": "snippet"}]))

        with patch("src.services.writing_services.AUDIT_TRIGGER_KEYWORDS", ["test"]):
            is_ok, reason, failures = await self.manager._run_causality_audits(
                1, mock_ctx, "content with test keyword", "blueprint", True, mock_monitor
            )

        assert is_ok is False
        assert "Causality failed" in reason
        assert len(failures) > 0

    @pytest.mark.asyncio
    async def test_apply_surgical_healing(self):
        """Test _apply_surgical_healing."""
        mock_ctx = MagicMock()
        mock_ctx.get.return_value = MagicMock()
        mock_ctx.get.return_value.settings = '{"active_constraints": []}'

        mock_monitor = MagicMock()
        mock_monitor.run_constraint_unit_tests = AsyncMock(return_value=(True, []))

        self.manager.surgical_causality_healing_pass = AsyncMock(return_value="Healed content")

        result, is_ok, reason = await self.manager._apply_surgical_healing(
            1, "content", mock_ctx, "blueprint", "reason", [{"fragment": "frag"}], mock_monitor
        )

        assert result == "Healed content"
        assert is_ok is True
        assert reason == ""

    @pytest.mark.asyncio
    async def test_apply_surgical_healing_failure(self):
        """Test _apply_surgical_healing failure."""
        mock_ctx = MagicMock()
        mock_ctx.get.return_value = None

        mock_monitor = MagicMock()
        mock_monitor.run_constraint_unit_tests = AsyncMock(return_value=(False, [{"constraint_index": 0}]))

        self.manager.surgical_causality_healing_pass = AsyncMock(return_value="")

        result, is_ok, reason = await self.manager._apply_surgical_healing(
            1, "content", mock_ctx, "blueprint", "reason", [{"fragment": "frag"}], mock_monitor
        )

        assert result == "content"
        assert is_ok is False
        assert "解消されませんでした" in reason

    @pytest.mark.asyncio
    async def test_run_dogfeeding_loop_skip(self):
        """Test _run_dogfeeding_loop skips for low importance."""
        mock_reporter = MagicMock()
        gen_ctx = WritingGenerationContext()

        result = await self.manager._run_dogfeeding_loop(
            1, "content", 0.5, 0.7, False, 0, 2, gen_ctx, mock_reporter
        )

        assert result is True
        mock_reporter.report.assert_called()

    @pytest.mark.asyncio
    async def test_run_dogfeeding_loop_retry(self):
        """Test _run_dogfeeding_loop triggers retry on low score."""
        mock_reporter = MagicMock()
        gen_ctx = WritingGenerationContext()

        self.mock_critique.run_dogfeeding_approval_loop = AsyncMock(
            return_value={"score": 70, "recommended_patch": "Patch text"}
        )

        result = await self.manager._run_dogfeeding_loop(
            1, "content", 0.5, 0.7, True, 0, 2, gen_ctx, mock_reporter
        )

        assert result is False
        assert gen_ctx.feedback_patch == "Patch text"

    @pytest.mark.asyncio
    async def test_run_dogfeeding_loop_pass(self):
        """Test _run_dogfeeding_loop passes on high score."""
        mock_reporter = MagicMock()
        gen_ctx = WritingGenerationContext()

        self.mock_critique.run_dogfeeding_approval_loop = AsyncMock(
            return_value={"score": 90}
        )

        result = await self.manager._run_dogfeeding_loop(
            1, "content", 0.5, 0.7, True, 0, 2, gen_ctx, mock_reporter
        )

        assert result is True

    @pytest.mark.asyncio
    async def test_register_lazy_patch(self):
        """Test _register_lazy_patch."""
        mock_reporter = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.book = MagicMock()
        mock_ctx.book.id = 1

        mock_repo = AsyncMock()
        mock_repo.get_latest_bible = AsyncMock(return_value=MagicMock(
            settings={"active_constraints": []},
            version=1,
        ))
        mock_repo.create_bible = AsyncMock()
        self.manager.repo = mock_repo

        await self.manager._register_lazy_patch(
            1, mock_ctx, False, 0.5, 0.7, False, "causal", False, mock_reporter
        )

        mock_repo.create_bible.assert_called_once()
        call_args = mock_repo.create_bible.call_args
        assert "遅延パッチ" in str(call_args)

    @pytest.mark.asyncio
    async def test_surgical_causality_healing_pass(self):
        """Test surgical_causality_healing_pass."""
        self.mock_pm.build_surgical_causality_healing_prompt = MagicMock(return_value="heal prompt")
        self.mock_llm.generate_text = AsyncMock()
        mock_res = MagicMock()
        mock_res.success = True
        mock_res.story_content = "Healed snippet"
        self.mock_llm.generate_text.return_value = mock_res

        result = await self.manager.surgical_causality_healing_pass(
            "Full content with target snippet",
            "world settings",
            "blueprint",
            "failure reason",
            ["target snippet"]
        )

        assert "Healed snippet" in result

    @pytest.mark.asyncio
    async def test_surgical_causality_healing_pass_no_replacement(self):
        """Test surgical healing when snippet not found."""
        self.mock_pm.build_surgical_causality_healing_prompt = MagicMock(return_value="heal prompt")
        self.mock_llm.generate_text = AsyncMock()
        mock_res = MagicMock()
        mock_res.success = True
        mock_res.story_content = "Healed"
        self.mock_llm.generate_text.return_value = mock_res

        result = await self.manager.surgical_causality_healing_pass(
            "Full content",
            "world",
            "blueprint",
            "reason",
            ["not in content"]
        )

        assert result == "Healed"


class TestWritingServicesIntegration:
    """Integration tests for writing services."""

    @pytest.mark.asyncio
    async def test_determine_pov_instruction_high_tension(self):
        """Test POV instruction for high tension."""
        manager = GenerationLoopManager(None, None, None, None, None, None)
        mock_reporter = MagicMock()

        result = manager._determine_pov_instruction(1, 85, False, mock_reporter)

        assert "幕間・視点変更" in result
        assert "敵役の絶望" in result or "ヒロイン" in result

    @pytest.mark.asyncio
    async def test_determine_pov_instruction_catharsis(self):
        """Test POV instruction for catharsis episode."""
        manager = GenerationLoopManager(None, None, None, None, None, None)
        mock_reporter = MagicMock()

        result = manager._determine_pov_instruction(1, 50, True, mock_reporter)

        assert "幕間・視点変更" in result

    @pytest.mark.asyncio
    async def test_determine_pov_instruction_normal(self):
        """Test POV instruction for normal episode."""
        manager = GenerationLoopManager(None, None, None, None, None, None)
        mock_reporter = MagicMock()

        result = manager._determine_pov_instruction(1, 50, False, mock_reporter)

        assert result == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])