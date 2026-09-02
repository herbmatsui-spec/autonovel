"""Server-Sent Events (SSE) によるリアルタイム生成テキスト配信ルーター。"""
from __future__ import annotations

import json
from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.domain.entities.easy_mode import EasyModeInput
from src.services.digest_service import process_chapter
from src.services.llm.factory import get_llm_adapter
from src.services.llm.prompts import NOVEL_SYSTEM_PROMPT, NOVEL_USER_PROMPT_TEMPLATE

router = APIRouter()


async def _stream_generator(input_data: EasyModeInput) -> AsyncIterator[str]:
    """LLM ストリーミング出力を SSE 形式で逐次 yield する。"""
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

    # 開始イベント送信
    yield f"data: {json.dumps({'type': 'start'}, ensure_ascii=False)}\n\n"

    try:
        max_tokens = max(500, min(8000, int(limit * 1.5)))
        async for chunk in adapter.stream_text(
            prompt=user_prompt,
            system_prompt=NOVEL_SYSTEM_PROMPT,
            max_tokens=max_tokens,
        ):
            yield f"data: {json.dumps({'type': 'chunk', 'text': chunk}, ensure_ascii=False)}\n\n"

        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
    except Exception as exc:
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)}, ensure_ascii=False)}\n\n"


@router.post("/generate/stream")
async def stream_generation(input_data: EasyModeInput) -> StreamingResponse:
    """小説執筆をストリーミング配信するエンドポイント。"""
    return StreamingResponse(
        _stream_generator(input_data),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
