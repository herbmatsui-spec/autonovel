import logging
import time
import urllib.parse
from typing import Any

from fastapi import APIRouter, Depends, Path, Request, Response
from pydantic import ValidationError

from src.backend import database
from src.backend.database.repository import BookRepository
from src.backend.observability import metrics
from src.backend.rate_limit import generate_limiter
from src.models.easy_mode_schemas import EasyModeInput, GenerationResponse
from src.services.digest_service import process_chapter
from src.services.llm.factory import get_llm_adapter
from src.services.llm.prompts import (
    NOVEL_SYSTEM_PROMPT,
    NOVEL_USER_PROMPT_TEMPLATE,
    SUGGESTIONS_PROMPT_TEMPLATE,
)
from src.services.marketing import MarketingAgent

router = APIRouter()
logger = logging.getLogger(__name__)


async def execute_generation(payload: dict[str, Any]) -> dict[str, Any]:
    """LLM アダプタを利用して非同期に小説本文と次話提案を生成する。"""
    start_time = time.time()
    current_chapter = payload.get("current_chapter", "")
    chapter_history = payload.get("chapter_history", [])
    character = payload.get("character", {})

    history_context = "\n".join(chapter_history[:-1]) if len(chapter_history) > 1 else "なし"
    user_prompt = NOVEL_USER_PROMPT_TEMPLATE.format(
        genre=character.get("genre", "ハイファンタジー (R15)"),
        char_name=character.get("name", "主人公"),
        char_personality=character.get("personality", "正義感が強い"),
        char_ability=character.get("ability", "剣術・魔導"),
        history_context=history_context,
        current_chapter=current_chapter,
    )

    adapter = get_llm_adapter()
    generated_text = await adapter.generate_text(
        prompt=user_prompt,
        system_prompt=NOVEL_SYSTEM_PROMPT,
        max_tokens=2000,
    )

    # 次話展開提案の生成
    suggestions_prompt = SUGGESTIONS_PROMPT_TEMPLATE.format(chapter_text=generated_text[:1000])
    try:
        suggestions_raw = await adapter.generate_text(
            prompt=suggestions_prompt,
            max_tokens=300,
        )
        suggestions = [
            line.lstrip("- ").strip()
            for line in suggestions_raw.strip().split("\n")
            if line.strip()
        ][:3]
    except Exception:
        logger.warning("Failed to generate suggestions, using defaults", exc_info=True)
        suggestions = [
            "新たな仲間との出会いと衝突",
            "古代遺跡に隠された真実の解明",
            "強敵の急襲と覚醒する未知の力",
        ]

    elapsed_ms = int((time.time() - start_time) * 1000)
    return {
        "output": generated_text,
        "suggestions": suggestions,
        "completion_time_ms": elapsed_ms,
    }


# 後方互換性エイリアス
generate_with_llm = execute_generation


@router.post("/generate", response_model=GenerationResponse)
async def generate_content(
    input_data: EasyModeInput,
    request: Request,
    session=Depends(database.get_db),
) -> GenerationResponse:
    generate_limiter.check(request)
    try:
        # 章の中身処理
        processed_chapter = process_chapter(input_data.current_chapter)

        # キャラクター設定を dict に変換
        char_dict = (
            input_data.character_params.model_dump()
            if hasattr(input_data.character_params, "model_dump")
            else dict(input_data.character_params)
        )

        # 生成パラメータ準備
        params: dict[str, Any] = {
            "chapter_history": input_data.chapter_history,
            "current_chapter": processed_chapter,
            "character": char_dict,
        }

        # タスクをキューに投入 (Huey 非同期タスク呼び出し)
        from src.backend.tasks.generation_tasks import generate_chapter_task

        task_result = generate_chapter_task(params)
        huey_task_id = str(task_result.id)
        params["task_id"] = huey_task_id

        # DB レコードを作成
        repo = BookRepository(session)
        repo.create_task(task_id=huey_task_id, status="running")

        metrics.increment("tasks_enqueued")
        logger.info("Enqueued generation task: task_id=%s", huey_task_id)

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
    except Exception as e:
        logger.exception("Internal generation error")
        from src.backend.exceptions import ServiceException

        raise ServiceException(detail=str(e)) from e


@router.get("/export/{book_id}")
async def export_easy_mode_package(
    book_id: int = Path(ge=1),
    session=Depends(database.get_db),
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
    """Return the status of a generation task.

    Returns "pending" if not yet completed, "failed" if an error occurred,
    otherwise "completed" with the result.
    """
    from src.backend.tasks.huey import huey

    result = huey.result(task_id)
    if result is None:
        logger.info("Task status polled (pending): task_id=%s", task_id)
        return {"task_id": task_id, "status": "pending"}

    if isinstance(result, dict) and result.get("error"):
        logger.info("Task status polled (failed): task_id=%s error=%s", task_id, result["error"])
        return {"task_id": task_id, "status": "failed", "error": result["error"], "result": result}

    logger.info("Task status polled (completed): task_id=%s", task_id)
    return {"task_id": task_id, "status": "completed", "result": result}


# Task cancellation endpoint (Step 69)
@router.delete("/task/{task_id}")
async def cancel_task(task_id: str, session=Depends(database.get_db)) -> dict[str, str]:
    """タスクをキャンセルまたは削除する。"""
    from src.backend.tasks.huey import huey

    # Hueyのタスクを取り消し試行
    try:
        huey.revoke_by_id(task_id)
    except Exception:
        logger.warning("Failed to revoke huey task_id=%s", task_id)

    # DBタスクのステータス更新
    repo = BookRepository(session)
    repo.update_task_status(task_id, "cancelled")

    return {"task_id": task_id, "status": "cancelled"}
