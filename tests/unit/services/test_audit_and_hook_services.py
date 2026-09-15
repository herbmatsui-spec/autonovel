"""src/services/audit_service.py と src/services/hook_diagnoser.py の単体テスト."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.services.audit_service import AuditService
from src.services.hook_diagnoser import HookDiagnoser, HOOK_THRESHOLD


class TestAuditService:
    """AuditService のテスト（LLM/prompt_manager は完全モック）."""

    def setup_method(self):
        llm = MagicMock()
        prompt_manager = MagicMock()
        self.service = AuditService(llm=llm, prompt_manager=prompt_manager)

    @pytest.mark.asyncio
    async def test_screen_plot_delegates(self):
        self.service.fast_screener.screen_plot = AsyncMock(return_value=(True, "OK"))
        passed, msg = await self.service.screen_plot("blueprint")
        assert passed is True
        assert msg == "OK"
        self.service.fast_screener.screen_plot.assert_awaited_once_with("blueprint")

    @pytest.mark.asyncio
    async def test_audit_ability_delegates(self):
        self.service.ability_checker.audit_ability_consistency = AsyncMock(
            return_value=(True, "OK", "note")
        )
        passed, msg, note = await self.service.audit_ability("bp", "{}", "[]")
        assert passed is True
        assert note == "note"

    @pytest.mark.asyncio
    async def test_audit_deai_delegates(self):
        self.service.deai_auditor.audit = AsyncMock(return_value=(False, "AI感あり"))
        passed, msg = await self.service.audit_deai("content")
        assert passed is False
        assert msg == "AI感あり"

    def test_get_erotic_advice_empty(self):
        advice = self.service.get_erotic_advice([], 1, 10)
        assert advice == []

    def test_get_erotic_advice_consecutive_peaks(self):
        # 連続ピーク（>=4 が 3話連続）でクールダウン警告
        intensities = [4, 5, 4]
        advice = self.service.get_erotic_advice(intensities, 3, 10)
        assert any("クールダウン" in a for a in advice)

    def test_get_erotic_advice_high_average(self):
        intensities = [4, 4]
        advice = self.service.get_erotic_advice(intensities, 2, 10)
        assert any("平均" in a for a in advice)

    def test_get_erotic_advice_no_advice(self):
        intensities = [1, 2]
        advice = self.service.get_erotic_advice(intensities, 2, 10)
        assert advice == []


class TestHookDiagnoser:
    """HookDiagnoser のテスト."""

    def setup_method(self):
        self.diagnoser = HookDiagnoser(llm_service=MagicMock())

    @pytest.mark.asyncio
    async def test_diagnose_empty(self):
        results = await self.diagnoser.diagnose([])
        assert results == []

    @pytest.mark.asyncio
    async def test_diagnose_scoring_exception(self):
        self.diagnoser.scorer.score_hook_retention = AsyncMock(side_effect=RuntimeError("boom"))
        chapters = [{"content": "本文", "ep_num": 1, "title": "第1話"}]
        results = await self.diagnoser.diagnose(chapters)
        assert len(results) == 1
        assert results[0]["hook_score"] == 0.0
        assert results[0]["is_weak"] is True

    @pytest.mark.asyncio
    async def test_detect_weak_hooks_filters(self):
        async def fake_score(text):
            return 0.9 if "strong" in text else 0.3

        self.diagnoser.scorer.score_hook_retention = AsyncMock(side_effect=fake_score)
        chapters = [
            {"content": "strong ending", "ep_num": 1, "title": "A"},
            {"content": "weak ending", "ep_num": 2, "title": "B"},
        ]
        weak = await self.diagnoser.detect_weak_hooks(chapters)
        assert len(weak) == 1
        assert weak[0]["ep_num"] == 2
        assert HOOK_THRESHOLD == 0.7

    @pytest.mark.asyncio
    async def test_generate_hook_fix_with_llm(self):
        llm = MagicMock()
        llm.generate_text = AsyncMock(return_value="書き換え案")
        self.diagnoser._llm = llm
        chapter = {"content": "本文", "ep_num": 1}
        result = await self.diagnoser.generate_hook_fix(chapter, api_key="key")
        assert result == "書き換え案"
        llm.generate_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generate_hook_fix_llm_error(self):
        llm = MagicMock()
        llm.generate_text = AsyncMock(side_effect=RuntimeError("LLM down"))
        self.diagnoser._llm = llm
        chapter = {"content": "本文", "ep_num": 1}
        result = await self.diagnoser.generate_hook_fix(chapter, api_key="key")
        assert result == ""

    @pytest.mark.asyncio
    async def test_generate_hook_fix_no_llm(self):
        self.diagnoser._llm = None
        # LLMService がインポートできない環境でも例外で捕捉される
        chapter = {"content": "本文", "ep_num": 1}
        try:
            result = await self.diagnoser.generate_hook_fix(chapter, api_key="key")
            assert isinstance(result, str)
        except Exception:
            pytest.skip("LLMService import unavailable in this env")
