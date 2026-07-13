
import pytest


@pytest.mark.asyncio
async def test_plot_repository(real_uow):
    async with real_uow as uow:
        # Create dependencies
        book_id = await uow.books.create_book("T", "G", "C", "S", 10, {}, {})
        branch_id = await uow.branches.create_branch(book_id, "main")

        # Test create_or_replace_plot
        await uow.plots.create_or_replace_plot(
            book_id=book_id,
            ep_num=1,
            thought_process="Thinking",
            title="Ep 1",
            summary="Sum",
            detailed_blueprint="BP",
            next_hook={"hook": "test"},
            tension=50,
            scenes=[],
            branch_id=branch_id
        )

        # Test get_plot
        plot = await uow.plots.get_plot(book_id_or_branch_id=branch_id, ep_num=1)
        assert plot is not None
        assert plot.title == "Ep 1"
        assert plot.tension == 50

        # Test get_all_plots
        plots = await uow.plots.get_all_plots(book_id_or_branch_id=branch_id)
        assert len(plots) == 1

        # Test update_plot_status_tension_love
        await uow.plots.update_plot_status_tension_love(branch_id, 1, tension_delta=10, love_meter=5)
        plot_updated = await uow.plots.get_plot(branch_id, 1)
        assert plot_updated.status == "completed"
        assert plot_updated.tension_delta == 10
        assert plot_updated.love_meter == 5

        # Test reset_plot_status
        await uow.plots.reset_plot_status(branch_id, 1)
        plot_reset = await uow.plots.get_plot(branch_id, 1)
        assert plot_reset.status == "planned"
        assert plot_reset.tension_delta == 0

        # Test update_plot_blueprint
        await uow.plots.update_plot_blueprint(branch_id, 1, "New BP")
        plot_bp = await uow.plots.get_plot(branch_id, 1)
        assert plot_bp.detailed_blueprint == "New BP"

        # Test delete_plots_from
        await uow.plots.delete_plots_from(branch_id, 1)
        plots_after = await uow.plots.get_all_plots(branch_id)
        assert len(plots_after) == 0
