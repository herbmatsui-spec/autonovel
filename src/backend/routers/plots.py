from fastapi import APIRouter
from config.container import Container
from src.backend.database.uow import UnitOfWork

router = APIRouter(prefix="/api/plots", tags=["plots"])

@router.get("/{book_id}")
async def get_plots(book_id: int):
    async with UnitOfWork(Container.db()) as uow:
        plots = await uow.plots.get_all_plots(book_id)
    return [
        {
            "ep_num": p.ep_num,
            "title": p.title,
            "summary": p.summary,
            "detailed_blueprint": p.detailed_blueprint,
            "tension": p.tension,
            "is_catharsis": p.is_catharsis,
            "status": p.status
        }
        for p in plots
    ]
