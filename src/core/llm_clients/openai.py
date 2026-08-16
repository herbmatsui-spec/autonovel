from __future__ import annotations

import asyncio
import time
from typing import Any, Callable, Dict, Optional, Tuple

from src.backend.engine_utils import AdaptiveCooldown, safe_model_validate
from src.backend.sanitizer import OutputSanitizer
from src.core.exceptions import LLMUnrecoverableError
from src.core.llm_clients.base import BaseLLMClient
from src.core.observability import StructuredLogger
from src.services.retry_decorator import RetryState, with_llm_retry

logger = StructuredLogger(__name__)


class OpenAIApiClient(BaseLLMClient):
    """OpenAI互換APIエンドポイントとの通信を担当。

    (vLLM, Ollama, OpenRouter, Together AI等に対応)
    """

    def __init__(self, cooldown: AdaptiveCooldown):
        self.cooldown = cooldown
        self._active_requests = 0

    @with_llm_retry()
    async def generate_json(
        self,
        model_name: str,
        prompt: str,
        system_instruction: Optional[str] = None,
        response_schema: Any = None,
        temp: float = 1.0,
        max_retries: int = 5,
        stream_callback: Optional[Callable[[str], None]] = None,
        retry_state: Optional[RetryState] = None,
    ) -> Tuple[Dict[str, Any], str, Any]:
        try:
            import openai
        except ImportError:
            raise ImportError(
                "OpenAI / Gemma integration requires the 'openai' python package. Please install it with 'pip install openai'."
            )

        from config.project_context import ProjectContext

        base_url = ProjectContext.get_setting("openai_base_url") or "https://api.openai.com/v1"
        api_key = ProjectContext.get_setting("openai_api_key") or "dummy"
        client = openai.AsyncOpenAI(base_url=base_url, api_key=api_key)

        current_temp = retry_state.temp if retry_state else temp
        current_model = retry_state.model_name if retry_state else model_name
        error_feedback = retry_state.error_feedback if retry_state else ""
        top_p = ProjectContext.get_setting("inference_top_p", 0.95)
        top_k = ProjectContext.get_setting("inference_top_k", 64)

        system_sandbox = ProjectContext.get_setting("system_sandbox", "")

        system_content = ""
        if system_sandbox:
            system_content += system_sandbox + "\n\n"
        if system_instruction:
            system_content += system_instruction

        messages = []
        if system_content:
            messages.append({"role": "system", "content": system_content})
        messages.append({"role": "user", "content": prompt})

        if error_feedback:
            messages[-1]["content"] = (
                f"【🚨出力形式エラー報告🚨】\n前回の出力に以下の不備がありました: {error_feedback}\n\n{prompt}"
            )

        if response_schema and hasattr(response_schema, "model_fields"):
            fields = list(response_schema.model_fields.keys())
            if "※重要:" not in messages[-1]["content"]:
                messages[-1]["content"] += (
                    f"\n\n※重要: JSONには以下のキーを必ず含めてください: {', '.join(fields)}"
                )
                messages[-1]["content"] += (
                    "\n\nCRITICAL: Output MUST be valid JSON ONLY. Start with '{' and end with '}'."
                )

        response_format = None
        if response_schema:
            response_format = {"type": "json_object"}

        extra_body = {}
        if top_k:
            extra_body["top_k"] = top_k

        start_time = time.time()
        try:
            from src.core.async_utils import safe_timeout

            async with safe_timeout(120.0):
                response = await client.chat.completions.create(
                    model=current_model,
                    messages=messages,
                    temperature=current_temp,
                    top_p=top_p,
                    response_format=response_format,
                    extra_body=extra_body if extra_body else None,
                )
        except asyncio.TimeoutError as e:
            raise TimeoutError(f"OpenAI API timed out after 120s: {e}")
        except Exception as e:
            err_msg = str(e).lower()
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
                logger.error(f"❌ Unrecoverable OpenAI API error: {e}")
                raise LLMUnrecoverableError(f"Unrecoverable OpenAI API error: {e}") from e
            if any(x in err_msg for x in ["429", "quota", "too many requests"]):
                from src.core.exceptions import LLMTemporaryError

                raise LLMTemporaryError(f"OpenAI Rate Limit: {e}") from e
            raise e

        full_text = response.choices[0].message.content or ""
        duration = time.time() - start_time

        usage_metadata = response.choices[0].usage
        prompt_tokens = usage_metadata.prompt_tokens if usage_metadata else 0
        completion_tokens = usage_metadata.completion_tokens if usage_metadata else 0

        class MockUsage:
            def __init__(self, p, c):
                self.prompt_token_count = p
                self.candidates_token_count = c

        usage = MockUsage(prompt_tokens, completion_tokens)

        metadata, story = OutputSanitizer.extract_content_and_metadata(full_text)

        if response_schema and hasattr(response_schema, "model_validate"):
            safe_model_validate(response_schema, metadata)

        self.cooldown.on_success()
        logger.info(
            f"✅ OpenAI Success: model={current_model}, len={len(prompt)}, dur={duration:.2f}s"
        )
        return metadata, story, usage
