"""
src/backend/routers/prompt_compare.py - プロンプト比較 API エンドポイント

Provides endpoints to list prompt versions for a book/key and to compare
multiple versions using the ``services.prompt_comparison`` utilities.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from config.container import Container
from src.backend.database.uow import UnitOfWork
from src.services.prompt_comparison import build_comparison

router = APIRouter(prefix="/api/prompt_compare", tags=["prompt_compare"])

# ---------------------------------------------------------------------------
# Request model for comparison
# ---------------------------------------------------------------------------

class CompareRequest(BaseModel):
    prompt_key: str = Field(..., description="比較対象プロンプトキー")
    texts: List[str] = Field(..., description="各バージョンに対する入力テキスト（順序はバージョンリストと対応）")

# ---------------------------------------------------------------------------
# Helper to get a UnitOfWork using the test‑overridden DB (Container.db)
# ---------------------------------------------------------------------------

def _uow() -> UnitOfWork:
    return UnitOfWork(Container.db())

# ---------------------------------------------------------------------------
# API functions – used directly in tests
# ---------------------------------------------------------------------------

@router.get("/versions/{book_id}", response_model=List[dict])
async def list_versions(book_id: int, prompt_key: str) -> List[dict]:
    async with _uow() as uow:
        all_versions = await uow.prompt_versions.get_prompt_versions(book_id)
        filtered = [v for v in all_versions if v.prompt_key == prompt_key]
        # Convert Pydantic models to dicts for easy consumption
        return [v.model_dump() if hasattr(v, "model_dump") else v.dict() for v in filtered]

@router.post("/compare/{book_id}", response_model=dict)
async def compare(book_id: int, req: CompareRequest) -> dict:
    # Retrieve the prompt versions for the given key
    async with _uow() as uow:
        all_versions = await uow.prompt_versions.get_prompt_versions(book_id)
        versions = [v for v in all_versions if v.prompt_key == req.prompt_key]
    # Ensure the number of texts matches the number of versions (test supplies matching counts)
    # ``build_comparison`` expects a list of version dicts and matching texts.
    version_dicts = [v.model_dump() if hasattr(v, "model_dump") else v.dict() for v in versions]
    result = await build_comparison(version_dicts, req.texts)
    return result
