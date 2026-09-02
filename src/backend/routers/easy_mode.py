import logging
import time
import urllib.parse
from typing import Any

from fastapi import APIRouter, Depends, Path, Request, Response
from pydantic import ValidationError

from src.backend import database
from src.backend.database.repository import BookRepository
from src.backend.observability.health import metrics
from src.backend.rate_limit import generate_limiter
from src.domain.entities.easy_mode import EasyModeInput, GenerationResponse
from src.services.digest_service import process_chapter
from src.services.graph_pipeline import graph_pipeline_service
from src.services.llm.factory import get_llm_adapter
from src.services.llm.prompts import (
    NOVEL_SYSTEM_PROMPT,
    NOVEL_USER_PROMPT_WITH_GRAPHRAG_TEMPLATE,
    SUGGESTIONS_PROMPT_TEMPLATE,
)
from src.services.marketing import MarketingAgent
from src.services.rag_service import rag_service

router = APIRouter()
logger = logging.getLogger(__name__)


async def execute_generation(payload: dict[str, Any]) -> dict[str, Any]:
    """LLM アダプタを利用して非同期に小説本文と次話提案を生成する (GraphRAG 統合済み)。"""
    start_time = time.time()
    current_chapter = payload.get("current_chapter", "")
    chapter_history = payload.get("chapter_history", [])
    character = payload.get("character", {})
    chapter_id = payload.get("chapter_id", 1)

    char_name = character.get("name", "主人公")
    genre = character.get("genre", "ハイファンタジー (R15)")
    personality = character.get("personality", "正義感が強い")
    ability = character.get("ability", "剣術・魔導")
    history_context = "\n".join(chapter_history[:-1]) if len(chapter_history) > 1 else "なし"

    # GraphRAG コンテキストの取得
    session = database.SessionLocal()
    try:
        graph_context, vector_context = rag_service.build_rag_context(
            session=session,
            current_prompt=current_chapter,
            character_name=char_name,
        )
    finally:
        session.close()

    # 文体（Style DNA）の解決とプロンプト注入
    from src.models.style_profile import StyleProfile
    from src.presets.loader import load_preset
    from src.services.cadence_reformatter import cadence_reformatter

    style_override = payload.get("style_override")
    style_id = character.get("style_id")

    style_profile: StyleProfile | None = None
    if isinstance(style_override, dict) and style_override:
        try:
            style_profile = StyleProfile(**style_override)
        except Exception as e:
            logger.warning("Failed to parse style_override: %s", e)

    if style_profile is None and style_id:
        try:
            preset_dict = load_preset(style_id)
            style_data = preset_dict.get("style", {})
            if isinstance(style_data, dict) and style_data:
                style_profile = StyleProfile(
                    id=style_id,
                    name=f"{style_id}調",
                    genre_hint=style_id,
                    **{k: v for k, v in style_data.items() if k in StyleProfile.model_fields},
                )
        except Exception:
            pass

    if style_profile is None:
        # デフォルトはジャンルから推定
        genre_key = "zarma" if "ざまぁ" in genre else "aku_reijo" if "令嬢" in genre else "cheat_tensei"
        try:
            preset_dict = load_preset(genre_key)
            style_data = preset_dict.get("style", {})
            if isinstance(style_data, dict) and style_data:
                style_profile = StyleProfile(
                    id=genre_key,
                    name=f"{genre_key}標準調",
                    genre_hint=genre_key,
                    **{k: v for k, v in style_data.items() if k in StyleProfile.model_fields},
                )
        except Exception:
            style_profile = StyleProfile(name=f"{genre}標準文体", genre_hint=genre)

    style_bias_section = style_profile.to_prompt_instruction() if style_profile else ""

    content_length_limit = int(payload.get("content_length_limit") or 2000)
    target_episodes = int(payload.get("target_episodes") or 1)
    llm_config = payload.get("llm_config") or {}

    # GraphRAG を反映したユーザープロンプトの構築
    user_prompt = NOVEL_USER_PROMPT_WITH_GRAPHRAG_TEMPLATE.format(
        genre=genre,
        char_name=char_name,
        char_personality=personality,
        char_ability=ability,
        style_bias_section=style_bias_section,
        graph_context=graph_context,
        vector_context=vector_context,
        history_context=history_context,
        current_chapter=current_chapter,
    )
    if content_length_limit:
        user_prompt += f"\n\n【執筆指示】1話あたりの目標文字数は約{content_length_limit}文字（目安: {max(500, content_length_limit - 300)}〜{content_length_limit + 300}文字）で執筆してください。"

    adapter = get_llm_adapter(
        provider=llm_config.get("provider"),
        api_key=llm_config.get("api_key"),
        model_name=llm_config.get("model_name"),
        base_url=llm_config.get("base_url"),
    )
    max_tokens = max(500, min(8000, int(content_length_limit * 1.5)))
    raw_generated_text = await adapter.generate_text(
        prompt=user_prompt,
        system_prompt=NOVEL_SYSTEM_PROMPT,
        max_tokens=max_tokens,
    )

    # ケイデンス・音律ポストプロセッサ（文末連続の自動排除・スマホ改行最適化）
    generated_text, cadence_stats = cadence_reformatter.reformat_novel_text(raw_generated_text)
    logger.info(
        "Cadence reformatted: %d repeated endings fixed across %d sentences (avg len: %.1f)",
        cadence_stats.repeated_endings_fixed,
        cadence_stats.total_sentences,
        cadence_stats.avg_sentence_length,
    )

    # 生成完了後、バックグラウンド/同期でナレッジグラフとベクトルを更新
    session = database.SessionLocal()
    try:
        graph_pipeline_service.process_chapter_knowledge(
            session=session,
            chapter_id=chapter_id,
            chapter_text=generated_text,
        )
    except Exception as e:
        logger.warning("Failed to process chapter knowledge in background: %s", e)
    finally:
        session.close()

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
    """章単位の対話型自動生成 [Interactive Writer]"""
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
            "content_length_limit": input_data.content_length_limit,
            "target_episodes": input_data.target_episodes,
            "style_override": input_data.style_override,
            "llm_config": (
                input_data.llm_config.model_dump()
                if input_data.llm_config and hasattr(input_data.llm_config, "model_dump")
                else input_data.llm_config
            ),
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


@router.delete("/task/{task_id}")
async def cancel_task(task_id: str) -> dict[str, str]:
    """タスクをキャンセルまたは削除する。"""
    from src.backend.tasks.huey import huey

    # Hueyのタスクを取り消し試行
    try:
        huey.revoke_by_id(task_id)
    except Exception:
        logger.warning("Failed to revoke huey task_id=%s", task_id)

    # DBタスクのステータス更新
    repo = BookRepository()
    repo.update_task_status(task_id, "cancelled")

    return {"task_id": task_id, "status": "cancelled"}



# --- ガチャ / ダイジェスト / 昇格 エンドポイント ---

from src.domain.entities.easy_mode import (
    DigestRequest,
    DigestResponse,
    ExportRequestPayload,
    GachaRequest,
    GachaResponse,
    PromotionRequest,
    PromotionResponse,
    ReversePlotGeneratePayload,
)
from src.services.digest_service import DigestService
from src.services.gacha_service import GachaService
from src.services.promotion_service import PromotionService


@router.post("/gacha", response_model=GachaResponse)
async def gacha_endpoint(req: GachaRequest) -> GachaResponse:
    """3案ガチャ企画生成 [Gacha Pitch]"""
    from src.backend.database.core import get_db_manager

    db = get_db_manager()
    svc = GachaService(db=db)
    return await svc.generate_plans(req)


@router.post("/digest", response_model=DigestResponse)
async def digest_endpoint(req: DigestRequest) -> DigestResponse:
    """ダイジェスト生成 [Quick Digest]"""
    from src.backend.database.core import get_db_manager

    db = get_db_manager()
    svc = DigestService(db=db)
    return await svc.create_digest(req)


@router.post("/promote", response_model=PromotionResponse)
async def promote_endpoint(req: PromotionRequest) -> PromotionResponse:
    """上級者モード昇格 [Producer Handoff]"""
    from src.backend.database.core import get_db_manager
    from fastapi import HTTPException

    db = get_db_manager()
    svc = PromotionService(db=db)
    try:
        return await svc.promote_book(req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/reverse-generate")
async def reverse_generate_endpoint(
    req: ReversePlotGeneratePayload,
) -> dict[str, Any]:
    """逆算プロットビルダー用同期生成エンドポイント [Reverse Plot Builder]"""
    from src.backend.workflows.reverse_plot_workflow import ReversePlotGenerationWorkflow

    workflow = ReversePlotGenerationWorkflow()
    return await workflow.execute(
        reporter=None,
        answers=req.answers,
        target_episodes=req.target_episodes,
        genre=req.genre,
        llm_config=req.llm_config,
    )


@router.post("/export-with-data")
async def export_with_data_endpoint(
    payload: ExportRequestPayload,
    book_id: int = 1,
    session=Depends(database.get_db),
) -> Response:
    """クライアントの最新ステート（本文・設定）を反映して即座にZIPパッケージをエクスポートする"""
    logger.info("Export with custom data requested: book_id=%s title=%s", book_id, payload.title)
    metrics.increment("exports_attempted")

    repo = BookRepository(session)
    # DBにも永続化
    try:
        repo.save_or_update_book_with_chapter(
            book_id=book_id,
            title=payload.title,
            genre=payload.genre,
            chapter_text=payload.current_text,
            character_params=payload.character,
            plots=payload.plots,
        )
    except Exception as e:
        logger.warning("Failed to auto-save book during export: %s", e)

    agent = MarketingAgent(repo=repo)
    book_data = {
        "title": payload.title,
        "genre": payload.genre,
        "chapters": [
            {
                "ep_num": 1,
                "title": "第1話 運命の覚醒",
                "content": payload.current_text or "本文未入力",
            }
        ],
        "characters": [
            {
                "name": payload.character.get("name", "主人公"),
                "role": "主人公",
                "personality": payload.character.get("personality", "設定なし"),
                "ability": payload.character.get("ability", "設定なし"),
            }
        ] if payload.character else [],
        "plots": payload.plots or [
            {
                "ep_num": 1,
                "title": "第1話 運命の覚醒",
                "one_line_summary": payload.current_text[:100] if payload.current_text else "冒険の始まり",
            }
        ],
        "bible_settings": {},
    }

    zip_bytes, zip_filename = await agent.create_export_package(book_id, book_data=book_data)

    encoded_filename = urllib.parse.quote(zip_filename)
    ascii_filename = zip_filename.encode("ascii", "ignore").decode("ascii") or "export.zip"
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


