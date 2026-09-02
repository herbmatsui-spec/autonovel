"""Server-Sent Events (SSE) によるリアルタイム生成テキスト配信ルーター。"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse

from src.backend.rate_limit import stream_limiter
from src.domain.entities.easy_mode import EasyModeInput, StreamQueryInput
from src.services.digest_service import process_chapter
from src.services.llm.factory import get_llm_adapter
from src.services.llm.prompts import NOVEL_SYSTEM_PROMPT, NOVEL_USER_PROMPT_TEMPLATE

logger = logging.getLogger(__name__)

router = APIRouter()


async def _check_disconnect(request: Request) -> bool:
    """クライアント切断を判定するヘルパ (テストでモンキーパッチ可能)。"""
    try:
        return await request.is_disconnected()
    except Exception:
        return False


async def _stream_generator(
    input_data: EasyModeInput, request: Request
) -> AsyncIterator[str]:
    """LLM ストリーミング出力を SSE 形式で逐次 yield する。

    クライアント切断時は ``adapter.cancel()`` を呼んで LLM への要求を停止する。
    """
    processed_chapter = process_chapter(input_data.current_chapter)
    char_dict = (
        input_data.character_params.model_dump()
        if hasattr(input_data.character_params, "model_dump")
        else dict(input_data.character_params)
    )

    history_context = (
        "\n".join(input_data.chapter_history[:-1])
        if len(input_data.chapter_history) > 1
        else (input_data.chapter_history[0] if input_data.chapter_history else "なし")
    )

    limit = input_data.content_length_limit or 2000
    genre = char_dict.get("genre", "ハイファンタジー (R15)")
    user_prompt = NOVEL_USER_PROMPT_TEMPLATE.format(
        genre=genre,
        char_name=char_dict.get("name", "主人公"),
        char_personality=char_dict.get("personality", "正義感が強い"),
        char_ability=char_dict.get("ability", "剣術・魔導"),
        history_context=history_context,
        current_chapter=processed_chapter,
    )
    user_prompt += f"\n\n【執筆指示】1話あたりの目標文字数は約{limit}文字（目安: {max(500, limit - 300)}〜{limit + 300}文字）で執筆してください。"

    llm_cfg = input_data.llm_config
    adapter = get_llm_adapter(
        provider=llm_cfg.provider if llm_cfg else None,
        api_key=llm_cfg.api_key if llm_cfg else None,
        model_name=llm_cfg.model_name if llm_cfg else None,
        base_url=llm_cfg.base_url if llm_cfg else None,
    )

    yield f"data: {json.dumps({'type': 'start'}, ensure_ascii=False)}\n\n"

    try:
        max_tokens = max(500, min(8000, int(limit * 1.5)))
        async for chunk in adapter.stream_text(
            prompt=user_prompt,
            system_prompt=NOVEL_SYSTEM_PROMPT,
            max_tokens=max_tokens,
        ):
            if await _check_disconnect(request):
                logger.info("SSE client disconnected; cancelling adapter")
                adapter.cancel()
                try:
                    from src.backend.observability.health import metrics

                    metrics.increment("streaming_disconnects")
                except Exception:
                    pass
                break
            yield f"data: {json.dumps({'type': 'chunk', 'text': chunk}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
    except asyncio.CancelledError:
        adapter.cancel()
        raise
    except Exception as exc:
        logger.exception("SSE stream error")
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"


@router.get("/generate/stream")
async def stream_generation(
    request: Request,
    payload: str | None = Query(
        default=None,
        description="Base64-urlsafe encoded JSON of EasyModeInput",
    ),
    current_chapter: str | None = Query(default=None),
    chapter_history: str | None = Query(
        default=None,
        description="newline-separated chapter history",
    ),
    character_name: str | None = Query(default=None),
    character_personality: str | None = Query(default=None),
    character_ability: str | None = Query(default=None),
    character_genre: str | None = Query(default=None),
    content_length_limit: int | None = Query(default=None, ge=1, le=10000),
) -> StreamingResponse:
    """小説執筆を SSE でストリーミング配信する (GET)。

    EventSource は GET のみ対応しているため、本エンドポイントは GET で
    リクエストパラメータ (個別フィールド または base64 ``payload``) を受け取り、
    ``text/event-stream`` で逐次チャンクを返す。

    個別フィールドが指定された場合は ``StreamQueryInput`` 経由で組み立てる。
    ``payload`` (base64 JSON) を渡した場合は ``EasyModeInput`` として直接復元する。
    """
    stream_limiter.check(request)

    if payload is not None:
        try:
            raw = base64.urlsafe_b64decode(payload.encode()).decode("utf-8")
            input_data = EasyModeInput.model_validate_json(raw)
        except Exception as exc:
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail=f"invalid payload: {exc}") from exc
    else:
        history_list = (
            [line for line in (chapter_history or "").split("\n") if line]
            if chapter_history is not None
            else None
        )
        query_input = StreamQueryInput(
            chapter_history=history_list,
            current_chapter=current_chapter,
            character_name=character_name,
            character_personality=character_personality,
            character_ability=character_ability,
            character_genre=character_genre,
            content_length_limit=content_length_limit,
        )
        input_data = query_input.to_easy_mode_input()

    return StreamingResponse(
        _stream_generator(input_data, request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/generate/stream", deprecated=True)
async def stream_generation_post(input_data: EasyModeInput) -> StreamingResponse:
    """【非推奨】``GET /generate/stream`` を使用してください。

    EventSource が GET 専用であるため、POST エンドポイントは互換性のためにのみ残す。
    内部的には ``_stream_generator`` を直接再利用せず、GET ハンドラへの切替を推奨する。
    """
    from fastapi import Request as _Request  # noqa: F401

    raise NotImplementedError(
        "POST /easy_mode/generate/stream は廃止予定です。GET /easy_mode/generate/stream を使用してください。"
    )
