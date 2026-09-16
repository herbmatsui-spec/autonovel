"""PlotDomainService（プロットドメインサービス）の単体テスト."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.domain.domain_services.plot_domain_service import (
    PlotDomainService, PlotStructureValidator, PlotIntegrityChecker, PlotValidationError,
)
from src.domain.entities.plot import Plot, Arc, PlotStatus, ChainPhase
from src.domain.value_objects.ids import NovelId, PlotId
from src.domain.value_objects.text import MarkdownText, TextContent


def make_mock_repo() -> MagicMock:
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    repo.get_by_episode = AsyncMock(return_value=None)
    repo.get_by_novel = AsyncMock(return_value=None)
    repo.save = AsyncMock(side_effect=lambda p: p)
    repo.save_arc = AsyncMock(side_effect=lambda a: a)
    repo.save_plot_point = AsyncMock(side_effect=lambda pp: pp)
    repo.delete = AsyncMock(return_value=True)
    repo.delete_arc = AsyncMock(return_value=True)
    repo.get_arcs_by_novel = AsyncMock(return_value=[])
    repo.list_by_branch = AsyncMock(return_value=[])
    repo.list_by_novel = AsyncMock(return_value=[])
    repo.get_plot_points = AsyncMock(return_value=[])
    return repo


def make_service() -> PlotDomainService:
    return PlotDomainService(plot_repo=make_mock_repo())


class TestPlotStructureValidator:
    """PlotStructureValidator のテスト."""

    def test_validate_plot_ok(self):
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        assert PlotStructureValidator.validate_plot(plot) == []

    def test_validate_plot_catharsis_out_of_range(self):
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        plot.catharsis = 150  # VOで守られていないフィールドを直接設定
        errors = PlotStructureValidator.validate_plot(plot)
        assert any("Catharsis" in e for e in errors)

    def test_validate_arc_ok(self):
        arc = Arc.create(novel_id=NovelId.generate(), name="a", description=MarkdownText("d"), start_episode=1, end_episode=5)
        assert PlotStructureValidator.validate_arc(arc) == []

    def test_validate_chain_phase_transition_valid(self):
        assert PlotStructureValidator.validate_chain_phase_transition(ChainPhase.FRICITON, ChainPhase.TURN) is True
        assert PlotStructureValidator.validate_chain_phase_transition(ChainPhase.TURN, ChainPhase.COUNTER_TURN) is True
        assert PlotStructureValidator.validate_chain_phase_transition(ChainPhase.COUNTER_TURN, ChainPhase.RESOLUTION) is True
        assert PlotStructureValidator.validate_chain_phase_transition(ChainPhase.RESOLUTION, ChainPhase.CATHARSIS) is True
        assert PlotStructureValidator.validate_chain_phase_transition(ChainPhase.CATHARSIS, ChainPhase.FRICITON) is True
        assert PlotStructureValidator.validate_chain_phase_transition(ChainPhase.MICRO_CATHARSIS, ChainPhase.FRICITON) is True

    def test_validate_chain_phase_transition_invalid(self):
        assert PlotStructureValidator.validate_chain_phase_transition(ChainPhase.FRICITON, ChainPhase.RESOLUTION) is False
        assert PlotStructureValidator.validate_chain_phase_transition(ChainPhase.RESOLUTION, ChainPhase.TURN) is False


class TestPlotIntegrityChecker:
    """PlotIntegrityChecker のテスト."""

    @pytest.mark.asyncio
    async def test_check_episode_continuity_not_found(self):
        repo = make_mock_repo()
        checker = PlotIntegrityChecker(repo)
        issues = await checker.check_episode_continuity(NovelId.generate(), NovelId.generate(), 1)
        assert issues == ["Plot for episode 1 not found"]

    @pytest.mark.asyncio
    async def test_check_episode_continuity_tension_jump(self):
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()
        repo = make_mock_repo()
        prev = Plot.create(novel_id=novel_id, branch_id=branch_id, episode_number=1, title="p")
        prev.set_tension(10)
        current = Plot.create(novel_id=novel_id, branch_id=branch_id, episode_number=2, title="c")
        current.set_tension(95)

        async def get_by_episode(n, b, ep):
            if ep == 2:
                return current
            if ep == 1:
                return prev
            return None

        repo.get_by_episode = AsyncMock(side_effect=get_by_episode)
        checker = PlotIntegrityChecker(repo)
        issues = await checker.check_episode_continuity(novel_id, branch_id, 2)
        assert any("tension jump" in i for i in issues)

    @pytest.mark.asyncio
    async def test_check_episode_continuity_status_regression(self):
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()
        repo = make_mock_repo()
        prev = Plot.create(novel_id=novel_id, branch_id=branch_id, episode_number=1, title="p")
        prev.change_status(PlotStatus.WRITING)
        current = Plot.create(novel_id=novel_id, branch_id=branch_id, episode_number=2, title="c")
        current.change_status(PlotStatus.PLANNED)

        async def get_by_episode(n, b, ep):
            if ep == 2:
                return current
            if ep == 1:
                return prev
            return None

        repo.get_by_episode = AsyncMock(side_effect=get_by_episode)
        checker = PlotIntegrityChecker(repo)
        issues = await checker.check_episode_continuity(novel_id, branch_id, 2)
        assert any("Status regression" in i for i in issues)

    @pytest.mark.asyncio
    async def test_check_arc_coverage(self):
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()
        repo = make_mock_repo()
        arc = Arc.create(novel_id=novel_id, name="アーク", description=MarkdownText("d"), start_episode=1, end_episode=5)
        plots = [Plot.create(novel_id=novel_id, branch_id=branch_id, episode_number=1, title="p1")]
        repo.get_arcs_by_novel = AsyncMock(return_value=[arc])
        repo.list_by_branch = AsyncMock(return_value=plots)
        checker = PlotIntegrityChecker(repo)
        result = await checker.check_arc_coverage(novel_id, branch_id)
        assert result["total_arcs"] == 1
        assert result["total_plots"] == 1
        assert {"arc": "アーク", "episode": 2} in result["gaps"]
        assert 0 < result["coverage_pct"] < 100


class TestPlotDomainServiceCRUD:
    """PlotDomainService のCRUD操作テスト."""

    @pytest.mark.asyncio
    async def test_create_plot_ok(self):
        service = make_service()
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()
        plot = await service.create_plot(novel_id, branch_id, 1, "第1話")
        assert plot.episode_number == 1
        service.plot_repo.save.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_create_plot_duplicate(self):
        service = make_service()
        novel_id = NovelId.generate()
        branch_id = NovelId.generate()
        existing = Plot.create(novel_id=novel_id, branch_id=branch_id, episode_number=1, title="x")
        service.plot_repo.get_by_episode = AsyncMock(return_value=existing)
        with pytest.raises(PlotValidationError):
            await service.create_plot(novel_id, branch_id, 1, "dup")

    @pytest.mark.asyncio
    async def test_update_plot_content_not_found(self):
        service = make_service()
        with pytest.raises(PlotValidationError):
            await service.update_plot_content(PlotId.generate(), title="x")

    @pytest.mark.asyncio
    async def test_update_plot_content_locked(self):
        service = make_service()
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        plot.lock()
        service.plot_repo.get_by_id = AsyncMock(return_value=plot)
        with pytest.raises(PlotValidationError):
            await service.update_plot_content(plot.id, title="x")

    @pytest.mark.asyncio
    async def test_set_plot_tension_range_error(self):
        service = make_service()
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        service.plot_repo.get_by_id = AsyncMock(return_value=plot)
        with pytest.raises(PlotValidationError):
            await service.set_plot_tension(plot.id, 150)

    @pytest.mark.asyncio
    async def test_set_plot_tension_ok(self):
        service = make_service()
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        service.plot_repo.get_by_id = AsyncMock(return_value=plot)
        result = await service.set_plot_tension(plot.id, 80, delta=20)
        assert result.tension_score.value == 80

    @pytest.mark.asyncio
    async def test_set_plot_catharsis(self):
        service = make_service()
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        service.plot_repo.get_by_id = AsyncMock(return_value=plot)
        result = await service.set_plot_catharsis(plot.id, 90, "大カタルシス")
        assert result.catharsis == 90

    @pytest.mark.asyncio
    async def test_advance_chain_phase_invalid(self):
        service = make_service()
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        service.plot_repo.get_by_id = AsyncMock(return_value=plot)
        with pytest.raises(PlotValidationError):
            await service.advance_chain_phase(plot.id, ChainPhase.RESOLUTION)

    @pytest.mark.asyncio
    async def test_advance_chain_phase_ok(self):
        service = make_service()
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        service.plot_repo.get_by_id = AsyncMock(return_value=plot)
        result = await service.advance_chain_phase(plot.id, ChainPhase.TURN)
        assert result.current_chain_phase == ChainPhase.TURN

    @pytest.mark.asyncio
    async def test_add_scene_locked(self):
        service = make_service()
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        plot.lock()
        service.plot_repo.get_by_id = AsyncMock(return_value=plot)
        with pytest.raises(PlotValidationError):
            await service.add_scene_to_plot(plot.id, "x")

    @pytest.mark.asyncio
    async def test_remove_scene_out_of_range(self):
        service = make_service()
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        service.plot_repo.get_by_id = AsyncMock(return_value=plot)
        with pytest.raises(PlotValidationError):
            await service.remove_scene_from_plot(plot.id, 5)

    @pytest.mark.asyncio
    async def test_lock_unlock_plot(self):
        service = make_service()
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        service.plot_repo.get_by_id = AsyncMock(return_value=plot)
        locked = await service.lock_plot(plot.id)
        assert locked.is_locked is True
        unlocked = await service.unlock_plot(plot.id)
        assert unlocked.is_locked is False

    @pytest.mark.asyncio
    async def test_change_plot_status(self):
        service = make_service()
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        service.plot_repo.get_by_id = AsyncMock(return_value=plot)
        result = await service.change_plot_status(plot.id, PlotStatus.WRITING)
        assert result.status == PlotStatus.WRITING

    @pytest.mark.asyncio
    async def test_get_plot_and_by_episode(self):
        service = make_service()
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        service.plot_repo.get_by_id = AsyncMock(return_value=plot)
        got = await service.get_plot(plot.id)
        assert got is plot

    @pytest.mark.asyncio
    async def test_create_arc_invalid_raises_at_construction(self):
        # Arc entity は __post_init__ で検証するため、不正値は ValueError として
        # 構築時に検出される（PlotValidationError の前段）
        service = make_service()
        with pytest.raises(ValueError):
            await service.create_arc(NovelId.generate(), "", MarkdownText("d"), 0, 0)

    @pytest.mark.asyncio
    async def test_create_arc_ok(self):
        service = make_service()
        arc = await service.create_arc(NovelId.generate(), "アーク", MarkdownText("d"), 1, 10)
        assert arc.get_span() == 10

    @pytest.mark.asyncio
    async def test_create_plot_point_not_found(self):
        service = make_service()
        with pytest.raises(PlotValidationError):
            await service.create_plot_point(PlotId.generate(), 1, TextContent("d"), "setup")

    @pytest.mark.asyncio
    async def test_create_plot_point_ok(self):
        service = make_service()
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        service.plot_repo.get_by_id = AsyncMock(return_value=plot)
        pp = await service.create_plot_point(plot.id, 1, TextContent("対立点"), "conflict")
        assert pp.type == "conflict"

    @pytest.mark.asyncio
    async def test_update_plot_scores(self):
        service = make_service()
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        service.plot_repo.get_by_id = AsyncMock(return_value=plot)
        result = await service.update_plot_scores(plot.id, state_integrity=85, emotional_resonance=70)
        assert result.state_integrity_score == 85

    @pytest.mark.asyncio
    async def test_add_healed_field(self):
        service = make_service()
        plot = Plot.create(novel_id=NovelId.generate(), branch_id=NovelId.generate(), episode_number=1, title="t")
        service.plot_repo.get_by_id = AsyncMock(return_value=plot)
        result = await service.add_healed_field(plot.id, "tension")
        assert "tension" in result.healed_fields

    @pytest.mark.asyncio
    async def test_delete_plot_and_arc(self):
        service = make_service()
        assert await service.delete_plot(PlotId.generate()) is True
        assert await service.delete_arc(PlotId.generate()) is True

    @pytest.mark.asyncio
    async def test_validate_episode_continuity_delegates(self):
        service = make_service()
        issues = await service.validate_episode_continuity(NovelId.generate(), NovelId.generate(), 1)
        assert issues == ["Plot for episode 1 not found"]

    @pytest.mark.asyncio
    async def test_check_arc_coverage_delegates(self):
        service = make_service()
        result = await service.check_arc_coverage(NovelId.generate(), NovelId.generate())
        assert result["total_arcs"] == 0
        assert result["coverage_pct"] == 100
