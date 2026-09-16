import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_expand_plot_raises_not_implemented():
    from src.application.use_cases.writing_use_cases import ExpandPlotUseCase
    from src.application.dtos.episode_dto import ExpandPlotDTO

    uc = ExpandPlotUseCase(episode_repo=AsyncMock(), novel_repo=AsyncMock(), uow=AsyncMock())
    with pytest.raises(NotImplementedError):
        await uc.execute(
            ExpandPlotDTO(
                plot_point_id="pt-1",
                novel_id="nov-1",
                branch_id="br-1",
                episode_number=1,
            )
        )
