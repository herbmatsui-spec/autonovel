"""backend/routers/workspace.py - ファイルシステムメモリ API"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

from src.backend.auth import require_api_key
from src.backend.database.uow import UnitOfWork
from src.core.container import AppContainer
from src.filesystem_memory.paths import get_workspace_path, WORKSPACE_FILES
from src.filesystem_memory.reader import read_file
from src.filesystem_memory.writer import write_file
from src.services.workspace_service import init_workspace

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


class FileContent(BaseModel):
    content: str
    metadata: Dict[str, Any] = {}


@router.post("/{book_id}/init", dependencies=[Depends(require_api_key)])
async def init_workspace_endpoint(book_id: int):
    async with UnitOfWork(AppContainer.db()) as uow:
        b = await uow.books.get_book(book_id)
    if not b:
        from src.core.exceptions import NotFoundError

        raise NotFoundError("Book not found", resource_type="Book", resource_id=str(book_id))

    book_dict = {
        "title": b.title,
        "genre": b.genre,
        "concept": b.concept,
        "synopsis": b.synopsis,
    }
    paths = init_workspace(book_id, book_dict)
    return {"message": "workspace initialized", "files": [str(p) for p in paths]}


@router.get("/{book_id}/files/{filename}", dependencies=[Depends(require_api_key)])
async def get_workspace_file(book_id: int, filename: str):
    if filename not in WORKSPACE_FILES:
        raise HTTPException(status_code=400, detail=f"Unknown file: {filename}")
    path = get_workspace_path(book_id) / filename
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return {"filename": filename, "content": read_file(path)}


@router.put("/{book_id}/files/{filename}", dependencies=[Depends(require_api_key)])
async def put_workspace_file(book_id: int, filename: str, payload: FileContent):
    if filename not in WORKSPACE_FILES:
        raise HTTPException(status_code=400, detail=f"Unknown file: {filename}")
    path = get_workspace_path(book_id) / filename
    write_file(path, payload.content)
    return {"message": "saved", "filename": filename}


@router.get("/{book_id}/memory/chapters", dependencies=[Depends(require_api_key)])
async def list_chapter_summaries(book_id: int):
    from src.filesystem_memory.reader import list_chapter_summaries

    files = list_chapter_summaries(book_id)
    result = []
    for f in files:
        # Extract ep_num from filename chapter_NN.md
        import re

        m = re.search(r"chapter_(\d+)", f.name)
        ep_num = int(m.group(1)) if m else None
        result.append({"ep_num": ep_num, "filename": f.name, "summary": read_file(f)})
    return {"chapters": result}
