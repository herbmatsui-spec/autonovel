"""CommercialBeatSheetWorkflow の単体テスト。"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
import pytest

from src.backend.workflows.commercial_beat_sheet_workflow import CommercialBeatSheetWorkflow
from src.models.beat_sheet import EpisodeBeat


def _beat(ep: int, tension: float = 0.5) -> EpisodeBeat:
    return EpisodeBeat(
        ep_num=ep,
        phase="開幕フック",
        mission=f"第{ep}話のミッション",
        tension_target=tension,
        visual_scene_focus="見せ場",
    )


def test_normalize_keeps_order_and_drops_duplicates():
    beats = [_beat(2), _beat(1), _beat(2)]
    out = CommercialBeatSheetWorkflow._normalize(beats, 40)
    assert [b.ep_num for b in out] == [1, 2]


def test_normalize_drops_out_of_range():
    from types import SimpleNamespace
    b0 = SimpleNamespace(ep_num=0)
    b41 = SimpleNamespace(ep_num=41)
    out = CommercialBeatSheetWorkflow._normalize([b0, b41, _beat(5)], 40)
    assert [b.ep_num for b in out] == [5]


def test_normalize_keeps_gaps_as_missing():
    out = CommercialBeatSheetWorkflow._normalize([_beat(1), _beat(3)], 40)
    assert [b.ep_num for b in out] == [1, 3]


def test_normalize_respects_target_episodes():
    out = CommercialBeatSheetWorkflow._normalize([_beat(1), _beat(30)], 20)
    assert [b.ep_num for b in out] == [1]


def test_normalize_empty_input():
    assert CommercialBeatSheetWorkflow._normalize([], 40) == []


async def _workflow_with_stub_agent(monkeypatch, beats):
    """PlanningAgent.generate_commercial_beat_sheet を固定したワークフローを作る。"""
    import src.backend.workflows.commercial_beat_sheet_workflow as mod

    fake_agent = MagicMock()
    fake_agent.generate_commercial_beat_sheet = AsyncMock(return_value=beats)
    monkeypatch.setattr(mod, "PlanningAgent", lambda **kwargs: fake_agent)

    # UnitOfWork をモックして DB 接続を不要にする
    mock_uow = MagicMock()
    mock_uow.__aenter__ = AsyncMock(return_value=mock_uow)
    mock_uow.__aexit__ = AsyncMock(return_value=None)
    mock_uow.plots = MagicMock()
    mock_uow.plots.create_or_replace_plot = AsyncMock()
    monkeypatch.setattr(mod, "UnitOfWork", lambda *args, **kwargs: mock_uow)

    wf = mod.CommercialBeatSheetWorkflow(repo=MagicMock(), prompt_manager=None, llm=None)
    return wf, mock_uow


@pytest.mark.asyncio
async def test_generate_persists_each_beat(monkeypatch):
    wf, mock_uow = await _workflow_with_stub_agent(monkeypatch, [_beat(1), _beat(2)])
    result = await wf.generate(book_id=1, title="T", synopsis="S")
    assert [b.ep_num for b in result] == [1, 2]
    assert mock_uow.plots.create_or_replace_plot.await_count == 2


@pytest.mark.asyncio
async def test_generate_does_not_delete_existing_plots(monkeypatch):
    """全削除せず upsert (create_or_replace_plot) のみ呼ぶこと。"""
    wf, mock_uow = await _workflow_with_stub_agent(monkeypatch, [_beat(1), _beat(2)])
    result = await wf.generate(book_id=1, title="T", synopsis="S")
    assert len(result) == 2
    assert not hasattr(mock_uow.plots, "delete") or mock_uow.plots.delete.call_count == 0


@pytest.mark.asyncio
async def test_generate_tolerates_agent_failure(monkeypatch):
    import src.backend.workflows.commercial_beat_sheet_workflow as mod

    fake_agent = MagicMock()
    fake_agent.generate_commercial_beat_sheet = AsyncMock(side_effect=RuntimeError("LLM失敗"))
    monkeypatch.setattr(mod, "PlanningAgent", lambda **kwargs: fake_agent)
    wf = mod.CommercialBeatSheetWorkflow(repo=MagicMock(), prompt_manager=None, llm=None)
    with pytest.raises(RuntimeError, match="LLM失敗"):
        await wf.generate(book_id=1, title="T", synopsis="S")
