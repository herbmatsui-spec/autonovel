import logging
import urllib.parse
from typing import Any

from fastapi import APIRouter, Depends, Path, Response
from pydantic import ValidationError

from src.backend import database
from src.backend.database.repository import BookRepository
from src.backend.observability import metrics
from src.models.easy_mode_schemas import EasyModeInput, GenerationResponse
from src.services.digest_service import process_chapter
from src.services.marketing import MarketingAgent

router = APIRouter()
logger = logging.getLogger(__name__)


async def generate_with_llm(payload: dict[str, Any]) -> dict[str, Any]:
    """Stub function to simulate asynchronous LLM generation.

    TODO: Replace with real LLM API call in production.
    """
    msg = "generate_with_llm is not implemented yet; replace with real LLM adapter."
    raise NotImplementedError(msg)


@router.post("/generate", response_model=GenerationResponse)
async def generate_content(
    input_data: EasyModeInput,
    session=Depends(database.get_db)
) -> GenerationResponse:
    try:
        # 章の中身処理
        processed_chapter = process_chapter(input_data.current_chapter)

        # 生成パラメータ準備
        params: dict[str, Any] = {
            "chapter_history": input_data.chapter_history,
            "current_chapter": processed_chapter,
            "character": input_data.character_params,
        }

        # DB セッションを利用、Task を作成
        repo = BookRepository(session)
        task = repo.create_task()
        task_id = task.id
        # タスク ID を payload に追加
        params["task_id"] = task_id

        # タスクステータスを "running" に更新
        repo.update_task_status(task_id, "running")

        # タスクをキューに投入 (関数内 import で循環参照回避)
        from src.backend.tasks.generation_tasks import generate_chapter_task

        task_result = generate_chapter_task(params)
        huey_task_id = str(getattr(task_result, "id", task_id))
        metrics.increment("tasks_enqueued")
        logger.info("Enqueued generation task: db_id=%s, huey_id=%s", task_id, huey_task_id)

        return GenerationResponse(
            task_id=huey_task_id,
            output="",
            completion_time_ms=0,
            error="",
            suggestions=[
                "生成タスク ID: "
                f"{huey_task_id} を投入しました。"
                f"ステータスを /easy_mode/status/{huey_task_id} で確認してください。"
            ],
        )
    except ValidationError as e:
        logger.warning("Validation error in generate_content: %s", e.errors())
        from src.backend.exceptions import ValidationException
        raise ValidationException(detail=str(e.errors())) from e
    except Exception:
        logger.exception("Internal generation error")
        from src.backend.exceptions import ServiceException
        raise ServiceException() from None


@router.get("/export/{book_id}")
async def export_easy_mode_package(
    book_id: int = Path(ge=1),
    session=Depends(database.get_db)
) -> Response:
    """かんたんモードで作成された作品の納品パッケージ (ZIP) をエクスポートする。

    book_id に対応する作品が DB に存在しなくてもフォールバックデータで
    ZIP を生成して返却する仕様 (TC-12 参照)。
    """
    logger.info("Export requested: book_id=%s", book_id)
    metrics.increment("exports_attempted")
    repo = BookRepository(session)
    agent = MarketingAgent(repo=repo)
    zip_bytes, zip_filename = await agent.create_export_package(book_id)

    encoded_filename = urllib.parse.quote(zip_filename)
    # RFC 6266: filename* は UTF-8 パーセントエンコード、filename は ASCII フォールバック
    ascii_filename = zip_filename.encode("ascii", "ignore").decode("ascii") or "export.zip"
    logger.info(
        "Export succeeded: book_id=%s bytes=%d filename=%s",
        book_id,
        len(zip_bytes),
        zip_filename,
    )
    metrics.increment("exports_succeeded")
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"
            ),
            "Cache-Control": "no-store",
        },
    )


# Task status endpoint
@router.get("/status/{task_id}")
async def get_task_status(task_id: str) -> dict[str, Any]:
    """
    Return the status of a generation task.

    Returns "pending" if not yet completed, otherwise includes result.
    """
    from src.backend.tasks.huey import huey

    result = huey.result(task_id)
    if result is None:
        logger.info("Task status polled (pending): task_id=%s", task_id)
        return {"task_id": task_id, "status": "pending"}
    logger.info("Task status polled (completed): task_id=%s", task_id)
    return {"task_id": task_id, "status": "completed", "result": result}
