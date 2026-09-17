import pytest
from unittest.mock import AsyncMock
from src.agents.specialists.unified_auditor import UnifiedAuditor

@pytest.mark.asyncio
async def test_unified_auditor_fallback():
    auditor = UnifiedAuditor(llm_gateway=None)
    report = await auditor.audit("「行こう！」彼は叫んだ。空が燃えていた。")
    assert report.final_score > 0.0
    assert isinstance(report.is_acceptable, bool)
    assert report.qualitative.critique != ""

@pytest.mark.asyncio
async def test_unified_auditor_with_mock_llm():
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = (
        '{"hook_score": 85, "emotional_score": 80, "character_consistency": 90, '
        '"overall_score": 85, "critique": "引きが強い", "actionable_patch": null}'
    )
    auditor = UnifiedAuditor(llm_gateway=mock_llm)
    report = await auditor.audit("「行こう！」彼は叫んだ。空が燃えていた。")
    assert report.qualitative.hook_score == 85.0
    assert report.qualitative.character_consistency == 90.0
    assert report.is_acceptable is True

@pytest.mark.asyncio
async def test_unified_auditor_character_plot_context():
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = (
        '{"hook_score": 90, "emotional_score": 88, "character_consistency": 95, '
        '"overall_score": 91, "critique": "令嬢の社会的仮面と内なる葛藤が秀逸", "actionable_patch": null}'
    )
    auditor = UnifiedAuditor(llm_gateway=mock_llm)
    report = await auditor.audit(
        text="「お待ちなさい」アリスは微笑んだ。その瞳の奥には冷たい決意があった。",
        character_profiles="アリス: 社会的仮面=おしとやかな令嬢, 内なる葛藤=復讐心",
        plot_spec="第1話: 舞踏会の裏で取引現場を目撃する (引き: Shocking Truth)",
    )
    assert report.qualitative.overall_score == 91.0
    assert "社会的仮面" in report.qualitative.critique
    # プロンプトに設定が渡されたことを検証
    called_prompt = mock_llm.generate.call_args[1]["prompt"]
    assert "おしとやかな令嬢" in called_prompt
    assert "Shocking Truth" in called_prompt
