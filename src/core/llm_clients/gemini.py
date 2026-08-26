from __future__ import annotations

import asyncio
import json
import re
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from google import genai  # type: ignore
from google.genai import types as genai_types

from src.backend.engine_utils import AdaptiveCooldown, safe_model_validate
from src.backend.sanitizer import OutputSanitizer
from src.core.exceptions import LLMUnrecoverableError
from src.core.llm_clients.base import BaseLLMClient
from src.core.observability import StructuredLogger
from src.models.base import get_gemini_schema
from src.services.retry_decorator import RetryState, with_llm_retry

logger = StructuredLogger(__name__)


class GeminiApiClient(BaseLLMClient):
    """Google GenAI SDK との低レベル通信を担当。

    リトライ、指数バックオフ、温度減衰、エラーハンドリングを集約する。
    """

    def __init__(self, client: genai.Client, cooldown: AdaptiveCooldown):
        self.client = client
        self.cooldown = cooldown
        self._active_requests = 0  # 現在の並行実行数を追跡

    @with_llm_retry()
    async def generate_json(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_schema: Any = None,
        temp: float = 0.7,
        max_retries: int = 5,
        stream_callback: Optional[Callable[[str], None]] = None,
        retry_state: Optional[RetryState] = None,
        nsfw_mode: bool = False,
    ) -> Tuple[Dict[str, Any], str, Any]:
        current_temp = retry_state.temp if retry_state else temp
        current_model = retry_state.model_name if retry_state else model_name
        error_feedback = retry_state.error_feedback if retry_state else ""
        attempt = retry_state.attempt if retry_state else 0

        start_time = time.time()

        # スキーマフォールバックモードの定義
        schema_modes = ["native", "clean_dict", "prompt_fallback"]
        if not response_schema:
            schema_modes = ["prompt_fallback"]

        last_error = None
        full_text = ""
        usage = None

        for mode in schema_modes:
            config = self.build_config_for_mode(
                system_instruction,
                current_temp,
                attempt,
                response_schema,
                mode,
                nsfw_mode=nsfw_mode,
            )

            full_prompt = prompt
            if error_feedback:
                full_prompt = f"【🚨出力形式エラー報告🚨】\n前回の出力に以下の不備がありました: {error_feedback}\n\n{prompt}"

            if response_schema:
                if mode == "prompt_fallback":
                    schema_dict = get_gemini_schema(response_schema)
                    schema_json = json.dumps(schema_dict, ensure_ascii=False, indent=2)
                    full_prompt += f"\n\n【出力スキーマ指示】\n以下のJSONスキーマ構造に完全に従って、JSONオブジェクトのみを出力してください。余計なマークダウンや説明は一切不要です。\n```json\n{schema_json}\n```"
                elif hasattr(response_schema, "model_fields"):
                    fields = list(response_schema.model_fields.keys())
                    full_prompt += (
                        f"\n\n※重要: JSONには以下のキーを必ず含めてください: {', '.join(fields)}"
                    )
                full_prompt += (
                    "\n\nCRITICAL: Output MUST be valid JSON ONLY. Start with '{' and end with '}'."
                )

            full_text = ""
            usage = None

            try:
                if stream_callback:
                    response_stream = self.client.models.generate_content_stream(
                        model=current_model, contents=full_prompt, config=config
                    )
                    for chunk in response_stream:
                        if chunk.text:
                            full_text += chunk.text
                            stream_callback(chunk.text)
                        if chunk.usage_metadata:
                            usage = chunk.usage_metadata
                else:

                    def _call():
                        # 404 NOT_FOUND 回避のため、モデル名に 'models/' プレフィックスが
                        # 付いていない場合は付与する
                        model_with_prefix = (
                            current_model
                            if current_model.startswith("models/")
                            else f"models/{current_model}"
                        )
                        return self.client.models.generate_content(
                            model=model_with_prefix, contents=full_prompt, config=config
                        )

                    try:
                        from src.core.async_utils import safe_timeout
                        from src.core.executor_manager import executor_manager

                        async with safe_timeout(120.0):
                            response = await executor_manager.run_io(_call)
                    except asyncio.TimeoutError as e:
                        raise TimeoutError(f"Gemini API timed out after 120s: {e}")
                    if not response or not response.text:
                        raise ValueError("API応答が空です。")

                    full_text = response.text
                    usage = getattr(response, "usage_metadata", None)

                last_error = None
                break
            except Exception as e:
                err_msg = str(e).lower()
                is_schema_error = any(
                    x in err_msg
                    for x in [
                        "schema",
                        "invalid argument",
                        "bad request",
                        "400",
                        "properties",
                        "additionalproperties",
                    ]
                )
                if is_schema_error and mode != "prompt_fallback":
                    logger.warning(
                        f"Gemini API schema error with mode '{mode}' (attempt={attempt}): {e}. Falling back to next schema mode."
                    )
                    last_error = e
                    continue
                else:
                    raise e

        if last_error:
            raise last_error

        metadata, story = OutputSanitizer.extract_content_and_metadata(full_text)

        if response_schema and hasattr(response_schema, "model_validate"):
            safe_model_validate(response_schema, metadata)

        duration = time.time() - start_time
        logger.info(
            f"✅ API Success: model={current_model}, len={len(prompt)}, dur={duration:.2f}s, parallel={self._active_requests}"
        )
        return metadata, story, usage

    @with_llm_retry()
    async def generate_text(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        temp: float = 0.7,
        max_retries: int = 5,
        stream_callback: Optional[Callable[[str], None]] = None,
        retry_state: Optional[RetryState] = None,
        nsfw_mode: bool = False,
    ) -> Tuple[str, Any]:
        current_temp = retry_state.temp if retry_state else temp
        current_model = retry_state.model_name if retry_state else model_name

        start_time = time.time()
        config = self.build_config_for_mode(
            system_instruction,
            current_temp,
            retry_state.attempt if retry_state else 0,
            None,
            "native",
            nsfw_mode=nsfw_mode,
        )

        try:
            from src.core.async_utils import safe_timeout
            from src.core.executor_manager import executor_manager

            if stream_callback:
                # ストリーミングは同期ジェネレータのため、別スレッドで実行して
                # イベントループをブロックしないようにする（google-genai SDK に
                # *_async メソッドは存在しない）。
                def _run_stream():
                    collected: List[str] = []
                    last_usage = None
                    # 404 NOT_FOUND 回避のため、モデル名に 'models/' プレフィックスが
                    # 付いていない場合は付与する
                    model_with_prefix = (
                        current_model
                        if current_model.startswith("models/")
                        else f"models/{current_model}"
                    )
                    for chunk in self.client.models.generate_content_stream(
                        model=model_with_prefix,
                        contents=prompt,
                        config=config,
                    ):
                        if getattr(chunk, "text", None):
                            text = chunk.text
                            if text:
                                collected.append(text)
                                try:
                                    stream_callback(text)
                                except Exception as e:
                                    logger.warning(f"Stream callback failed: {e}")
                        if getattr(chunk, "usage_metadata", None):
                            last_usage = chunk.usage_metadata
                    return "".join(collected), last_usage

                async with safe_timeout(180.0):
                    # 移行計画メモ: 全ブロッキングI/Oは executor_manager.run_io() に統一
                    # (asyncio.to_thread は executor_manager の IO プールへ移行済み)。
                    full_text, usage = await executor_manager.run_io(_run_stream)
            else:

                def _run_once():
                    # 404 NOT_FOUND 回避のため、モデル名に 'models/' プレフィックスが
                    # 付いていない場合は付与する
                    model_with_prefix = (
                        current_model
                        if current_model.startswith("models/")
                        else f"models/{current_model}"
                    )
                    return self.client.models.generate_content(
                        model=model_with_prefix,
                        contents=prompt,
                        config=config,
                    )

                async with safe_timeout(120.0):
                    response = await executor_manager.run_io(_run_once)
                full_text = response.text
                usage = getattr(response, "usage_metadata", None)

            story = OutputSanitizer._clean_story(full_text)

            duration = time.time() - start_time
            logger.info(
                f"✅ Text API Success: model={current_model}, len={len(prompt)}, dur={duration:.2f}s"
            )
            return story, usage

        except Exception as e:
            raise e

    def build_config(
        self,
        system_instruction: Optional[str],
        temp: float,
        attempt: int,
        response_schema: Any = None,
    ) -> genai_types.GenerateContentConfig:
        return self.build_config_for_mode(
            system_instruction, temp, attempt, response_schema, "native"
        )

    def build_config_for_mode(
        self,
        system_instruction: Optional[str],
        temp: float,
        attempt: int,
        response_schema: Any,
        mode: str,
        nsfw_mode: bool = False,
    ) -> genai_types.GenerateContentConfig:
        # リトライごとに温度を下げることで、AIの迷走を抑える
        current_temp = max(0.0, temp - (attempt * 0.15))

        config = genai_types.GenerateContentConfig(
            temperature=current_temp,
            system_instruction=system_instruction,
        )

        # NSFWモード時のみセーフティフィルターを緩和
        if nsfw_mode:
            config.safety_settings = [
                genai_types.SafetySetting(
                    category=genai_types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=genai_types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
            ]

        if response_schema:
            config.response_mime_type = "application/json"
            if mode == "native":
                config.response_schema = response_schema
            elif mode == "clean_dict":
                schema_dict = get_gemini_schema(response_schema)
                config.response_schema = schema_dict

        return config

    async def _handle_error(
        self, e: Exception, model_name: str, attempt: int, max_retries: int
    ) -> bool:
        err_msg = str(e).lower()
        if any(
            x in err_msg
            for x in [
                "429",
                "quota",
                "503",
                "unavailable",
                "500",
                "502",
                "internal",
                "bad gateway",
            ]
        ):
            retry_match = re.search(r"retry\s+in\s+([\d\.]+)", err_msg)
            if retry_match:
                base_wait = float(retry_match.group(1))
            else:
                base_wait = 2.0**attempt

            wait_time = min(base_wait, 60.0)
            logger.warning(
                f"Retrying (Attempt {attempt + 1}) after {wait_time:.1f}s due to API congestion."
            )
            self.cooldown.on_rate_limit()
            await asyncio.sleep(wait_time)
            return True

        if any(
            x in err_msg
            for x in [
                "401",
                "403",
                "unauthorized",
                "invalid key",
                "api key",
                "404",
                "not found",
                "400",
                "bad request",
            ]
        ):
            logger.error(f"❌ Unrecoverable Gemini API error: {e}")
            raise LLMUnrecoverableError(f"Unrecoverable Gemini API error: {e}") from e

        return False
