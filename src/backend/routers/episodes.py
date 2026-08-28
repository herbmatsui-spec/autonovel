from fastapi import APIRouter, Depends

from src.backend.auth import require_api_key
from src.backend.database.uow import UnitOfWork
from src.backend.task_helpers import create_task as _create_task
from src.backend.router_helpers import workflow_endpoint
from src.backend.response_helpers import api_success
from src.backend.utils.id_generator import generate_prefixed_id as generate_task_id
from src.core.container import AppContainer
from src.core.observability import TraceContext
from src.models.api_schemas import (
    ChapterImportRequest,
    EpisodeGenerateCandidatesRequest,
    EpisodeGenerateRequest,
    RetryFailedRequest,
)

router = APIRouter(prefix="/api/episodes", tags=["episodes"])


@router.get("/chapters/{book_id}")
async def get_chapters(book_id: int):
    async with UnitOfWork(AppContainer.db()) as uow:
        chapters = await uow.chapters.get_all_non_anchor_chapters(book_id)
    return [
        {
            "ep_num": c.ep_num,
            "title": c.title,
            "content": c.content,
            "summary": c.summary,
            "created_at": c.created_at,
        }
        for c in chapters
    ]


def generate_task_id(prefix: str) -> str:
    import uuid

    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@workflow_endpoint("episode_generate")
@router.post("/generate")
async def generate_episodes(req: EpisodeGenerateRequest, api_key: str = Depends(require_api_key)):
    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("write")
    await _create_task(
        task_id, "執筆タスクを開始中...", total_steps=req.write_to - req.write_from + 1
    )
    execute_service_workflow(
        task_id=task_id,
        api_key=api_key,
        config_dict=req.config,
        method_name="episode_writing_workflow",
        kwargs={
            "book_id": req.book_id,
            "write_from": req.write_from,
            "write_to": req.write_to,
            "passion": req.passion,
            "word_count": req.word_count,
            "do_refine": req.do_refine,
            "env_state": req.env_state,
            "pipeline_mode": req.pipeline_mode,
            "mode": "final",
        },
        trace_id=TraceContext.get_trace_id(),
    )
    return api_success({"task_id": task_id}, "エピソード生成を開始しました")


@workflow_endpoint("episode_generate_candidates")
@router.post("/generate_candidates")
async def generate_episodes_candidates(req: EpisodeGenerateCandidatesRequest, api_key: str = Depends(require_api_key)):
    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("write_candidates")
    await _create_task(
        task_id, "本文候補案を生成中...", total_steps=req.write_to - req.write_from + 1
    )
    execute_service_workflow(
        task_id=task_id,
        api_key=api_key,
        config_dict=req.config,
        method_name="episode_writing_workflow",
        kwargs={
            "book_id": req.book_id,
            "write_from": req.write_from,
            "write_to": req.write_to,
            "passion": req.passion,
            "word_count": req.word_count,
            "do_refine": req.do_refine,
            "env_state": req.env_state,
            "pipeline_mode": req.pipeline_mode,
            "mode": "candidates",
        },
        trace_id=TraceContext.get_trace_id(),
    )
    return api_success({"task_id": task_id}, "エピソード候補生成を開始しました")


@workflow_endpoint("episode_retry_failed")
@router.post("/retry_failed")
async def retry_failed_episodes(req: RetryFailedRequest, api_key: str = Depends(require_api_key)):
    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("retry_failed")
    await _create_task(task_id, "失敗エピソードの修復を開始中...", total_steps=1)
    execute_service_workflow(
        task_id=task_id,
        api_key=api_key,
        config_dict=req.config,
        method_name="retry_failed_episodes_workflow",
        kwargs={"book_id": req.book_id, "passion": req.passion, "word_count": req.word_count},
        trace_id=TraceContext.get_trace_id(),
    )
    return api_success({"task_id": task_id}, "失敗エピソード修復を開始しました")


@workflow_endpoint("episode_import_chapter")
@router.post("/chapters/import")
async def import_chapter(req: ChapterImportRequest, api_key: str = Depends(require_api_key)):
    from src.backend.tasks import execute_service_workflow

    task_id = generate_task_id("import")
    await _create_task(task_id, "手書き原稿のインポートと研磨を開始中...", total_steps=1)
    execute_service_workflow(
        task_id=task_id,
        api_key=api_key,
        config_dict={},
        method_name="chapter_import_workflow",
        kwargs={
            "book_id": req.book_id,
            "ep_num": req.ep_num,
            "import_text": req.import_text,
            "do_refine": req.do_refine,
        },
        trace_id=TraceContext.get_trace_id(),
    )
    return api_success({"task_id": task_id}, "原稿インポートを開始しました")
