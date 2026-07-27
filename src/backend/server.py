from fastapi import FastAPI

from src.backend.routers import easy_mode

app = FastAPI(title="AutoNovel Backend")
app.include_router(easy_mode.router, prefix="/easy_mode", tags=["easy_mode"])


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
