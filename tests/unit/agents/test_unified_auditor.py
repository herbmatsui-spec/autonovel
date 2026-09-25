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

@pytest.mark.asyncio
async def test_unified_auditor_conflicts_generation():
    auditor = UnifiedAuditor(llm_gateway=None)
    # 会話文のない長めの文章
    text = "長い文章が続く。彼は歩いた。街は静まり返っていた。太陽が沈み、闇が支配した。"
    report = await auditor.audit(text)
    assert isinstance(report.conflicts, list)
    # dialogue_ratio が低いため dialogue カテゴリの指摘が含まれるか確認
    dialogue_conflicts = [c for c in report.conflicts if c.category == "dialogue"]
    assert len(dialogue_conflicts) > 0

@pytest.mark.asyncio
async def test_unified_auditor_actionable_patch_conflict():
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = (
        '{"hook_score": 60, "emotional_score": 65, "character_consistency": 70, '
        '"overall_score": 65, "critique": "冒頭の引きが弱いため修正を推奨", '
        '"actionable_patch": "「待て！」背後から鋭い叫び声が響いた。"}'
    )
    auditor = UnifiedAuditor(llm_gateway=mock_llm)
    report = await auditor.audit("彼はゆっくりと歩き始めた。")
    assert report.is_acceptable is False
    patch_conflicts = [c for c in report.conflicts if c.suggested_value == "「待て！」背後から鋭い叫び声が響いた。"]
    assert len(patch_conflicts) == 1
    assert patch_conflicts[0].category == "hook"

